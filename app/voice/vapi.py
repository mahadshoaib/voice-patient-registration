import json
import re

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.exceptions import AppError
from app.core.logging import event
from app.voice.tools import execute, get_registration, validation_result


class FunctionCall(BaseModel):
    name: str
    arguments: dict | str = Field(default_factory=dict)


class ToolCall(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    function: FunctionCall


class Call(BaseModel):
    id: str = Field(min_length=1, max_length=100)


class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: str
    call: Call
    toolCallList: list[ToolCall] = Field(default_factory=list, max_length=20)
    status: str | None = None
    artifact: dict = Field(default_factory=dict)


def optional_offer_answered(artifact: dict) -> bool:
    """Check provider conversation evidence, not an LLM's offered=true assertion.

    Fail closed without history. Do not retain the transcript in our database.
    A restart requires a fresh offer. Adjacent bot fragments are combined.
    """
    messages = artifact.get("messages", [])
    if not isinstance(messages, list):
        return False
    bot_text = ""
    offered = False
    answered = False
    for message in messages:
        if not isinstance(message, dict):
            continue
        if any(
            t.get("function", {}).get("name") == "start_over"
            for t in message.get("toolCalls", [])
            if isinstance(t, dict)
        ):
            bot_text, offered, answered = "", False, False
        role = message.get("role")
        text = message.get("message") or message.get("content") or ""
        if not isinstance(text, str):
            continue
        if role in {"bot", "assistant"}:
            bot_text += " " + text.lower()
            categories = (
                r"\bemail\b",
                r"\binsurance\b",
                r"\bemergency contact\b",
                r"\b(apartment|unit)\b",
                r"\blanguage\b",
            )
            if all(re.search(pattern, bot_text) for pattern in categories) and re.search(
                r"\b(would you like|do you want|anything.*add|like to add)\b", bot_text
            ):
                offered = True
        elif role == "user":
            reply = text.strip().lower().strip(".!? ")
            if offered and reply and reply not in {"what", "huh", "repeat that", "say that again"}:
                answered = True
            bot_text = ""
    return answered


class Webhook(BaseModel):
    message: Message


def process(db: Session, message: Message) -> dict:
    from pydantic import ValidationError

    call_id = message.call.id
    if message.type != "tool-calls":
        if message.type == "end-of-call-report" or (
            message.type == "status-update" and message.status == "ended"
        ):
            reg = get_registration(db, call_id)
            saved = reg.patient_id is not None
            reg.status, reg.confirmation_token, reg.draft = "ended", None, {}
            reg.field_errors, reg.refusals = {}, {}
            reg.appointment_slot = reg.appointment_token = reg.booking_patient_id = None
            db.commit()
            event("call_ended", call_id=call_id, saved=saved)
        elif message.type == "status-update" and message.status == "in-progress":
            get_registration(db, call_id)
            db.commit()
        return {"data": {"received": True}, "error": None}

    results = []
    for tool in message.toolCallList:
        try:
            args = tool.function.arguments
            if isinstance(args, str):
                args = json.loads(args)
            if not isinstance(args, dict):
                raise ValueError("Tool arguments must be an object")
            if tool.function.name == "prepare_confirmation" and not optional_offer_answered(
                message.artifact
            ):
                raise AppError(
                    400,
                    "optional_offer_required",
                    "Before read-back, ask: Would you like to add email, insurance, an emergency "
                    "contact, an apartment or unit, or a preferred language? WAIT for the caller's "
                    "answer, collect any additions, then call prepare_confirmation again. "
                    "Conversation history must show this offer and the caller's response.",
                )
            result = execute(db, call_id, tool.function.name, args)
            db.commit()
            if result.get("success") and not result.get("already_saved"):
                save_event = {
                    "create_patient": "patient_created",
                    "update_patient": "patient_updated",
                }.get(tool.function.name)
                if save_event:
                    event(save_event, call_id=call_id, patient_id=result["patient_id"])
        except ValidationError as exc:
            db.rollback()
            result = validation_result(exc)
        except AppError as exc:
            db.rollback()
            result = {
                "success": False,
                "error_type": exc.code,
                "message": exc.message,
                "field_errors": exc.details or {},
            }
        except (ValueError, TypeError) as exc:
            db.rollback()
            result = {"success": False, "error_type": "validation_error", "message": str(exc)}
        except (IntegrityError, StaleDataError):
            db.rollback()
            result = {
                "success": False,
                "error_type": "conflict",
                "message": "Record changed concurrently; collect current fields and reconfirm",
            }
        except SQLAlchemyError as exc:
            db.rollback()
            event("write_failure", call_id=call_id, error_type=type(exc).__name__)
            result = {
                "success": False,
                "error_type": "system_error",
                "message": (
                    "Registration has not been confirmed as saved. Please try again shortly."
                ),
            }
        # Vapi uses its own protocol envelope, not the public REST envelope.
        results.append({"toolCallId": tool.id, "result": json.dumps(result, default=str)})
    return {"results": results}
