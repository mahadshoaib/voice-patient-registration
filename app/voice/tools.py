import re
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import event
from app.models.registration import Registration
from app.schemas.patient import REQUIRED_FIELDS, PatientCreate, PatientRead, validate_fields
from app.services.patient_service import PatientService
from app.voice.appointments import BOOKING_TOOLS, execute_booking

CONFIRMATIONS = {
    "yes",
    "correct",
    "that's right",
    "that is right",
    "looks good",
    "everything is correct",
    "yes that's correct",
    "yes correct",
    "this is correct",
    "that's correct",
    "that is correct",
    "yes this is correct",
    "yes that is correct",
    "yes everything is correct",
    "yes that's right",
    "yes that is right",
    "yes looks good",
    "yes please",
    "yes this is correct now",
    "this is correct now",
}


def explicit_confirmation(value) -> bool:
    if not isinstance(value, str):
        return False
    # Normalize punctuation, never accept a prefix: "yes, but ..." is not consent.
    normalized = re.sub(r"[.,!?;:]", " ", value.lower().replace("’", "'"))
    normalized = re.sub(r"\b(um|uh)\b", " ", normalized)
    return " ".join(normalized.split()) in CONFIRMATIONS


def snapshot(registration: Registration) -> dict:
    return {
        "success": not bool(registration.field_errors),
        "draft": registration.draft,
        "missing_required": sorted(REQUIRED_FIELDS - registration.draft.keys()),
        "field_errors": registration.field_errors,
        "status": registration.status,
    }


def update_permission(value) -> bool:
    """Permission to open an edit is distinct from confirmation to persist it."""
    if explicit_confirmation(value):
        return True
    if not isinstance(value, str):
        return False
    text = value.lower().replace("’", "'")
    if re.search(r"\b(no|not|don't|do not|never|maybe|later|cancel|stop|unsure)\b", text):
        return False
    return bool(
        re.search(
            r"\b(i want to|i would like to|i'd like to|please) "
            r"(update|correct|change|fix|add|edit|remove)\b",
            text,
        )
    )


def update_choice(patient) -> dict:
    return {
        "patient": {
            "patient_id": str(patient.patient_id),
            "first_name": patient.first_name,
            "last_name": patient.last_name,
        },
        "next_action": "accept_existing_update",
        "message": "An existing record was found. Ask permission to update if not already given, "
        "then call accept_existing_update with patient_id and the caller's exact response. "
        "Do not ask for DOB, sex, or address again: those fields have not been loaded yet. "
        "If permission is declined, ask for another phone or end without saving.",
    }


def failed_step(reg: Registration, counter: str, next_action: str, message: str) -> dict:
    # Return a result rather than raising: the webhook must commit the retry count.
    counts = dict(reg.refusals)
    counts[counter] = counts.get(counter, 0) + 1
    reg.refusals = counts
    if counts[counter] >= 3:
        reg.status, reg.confirmation_token = "cancelled", None
        reg.draft, reg.field_errors = {}, {}
        return {
            "success": False,
            "error_type": "retry_limit_reached",
            "end_call": True,
            "next_action": "endCall",
            "message": "Stop retrying. Nothing was saved in this call. Apologize briefly, "
            "ask the caller to try again later, and call endCall now.",
        }
    return {
        "success": False,
        "error_type": "confirmation_required",
        "next_action": next_action,
        "message": message,
        "attempts_remaining": 3 - counts[counter],
    }


def get_registration(db: Session, call_id: str) -> Registration:
    registration = db.scalar(
        select(Registration).where(Registration.call_id == call_id).with_for_update()
    )
    if registration is None:
        registration = Registration(call_id=call_id, draft={}, field_errors={}, refusals={})
        db.add(registration)
        db.flush()
        event("call_started", call_id=call_id)
    return registration


def readback(payload: PatientCreate) -> str:
    p = payload.model_dump()
    number = p["phone_number"]
    spoken_phone = ", ".join(" ".join(chunk) for chunk in (number[:3], number[3:6], number[6:]))
    birth = payload.date_of_birth
    address = ", ".join(
        str(p[k]) for k in ("address_line_1", "address_line_2", "city", "state", "zip_code") if p[k]
    )
    parts = [
        "Before I save this, let me make sure I have everything right.",
        f"Your name is {p['first_name']} {p['last_name']}.",
        f"Your date of birth is {birth.strftime('%B')} {birth.day}, {birth.year}.",
        f"Your phone number is {spoken_phone}.",
        f"Your address is {address}.",
        f"You selected {p['sex']}.",
    ]
    for key in (
        "email",
        "insurance_provider",
        "insurance_member_id",
        "preferred_language",
        "emergency_contact_name",
        "emergency_contact_phone",
    ):
        if p[key]:
            parts.append(f"Your {key.replace('_', ' ')} is {p[key]}.")
    return " ".join(parts + ["Is all of that correct?"])


def execute(db: Session, call_id: str, name: str, args: dict) -> dict:
    event("tool_invocation", call_id=call_id, tool=name)
    reg = get_registration(db, call_id)
    service = PatientService(db)
    if reg.status in {"ended", "cancelled"}:
        return {
            "success": False,
            "error_type": "call_closed",
            "end_call": True,
            "next_action": "endCall",
            "message": "This call is closed. Do not retry; endCall now.",
        }
    if name in BOOKING_TOOLS:
        return execute_booking(db, reg, name, args)
    if reg.status == "saved":
        if name in {"create_patient", "update_patient"}:
            return {"success": True, "patient_id": str(reg.patient_id), "already_saved": True}
        raise AppError(409, "already_saved", "Registration is already saved; end the call")

    if name == "start_over":
        reg.booking_patient_id = reg.appointment_slot = reg.appointment_token = None
        reg.draft, reg.field_errors, reg.refusals = {}, {}, {}
        reg.confirmation_token, reg.update_patient_id = None, None
        reg.status = "collecting"
        return snapshot(reg)

    if name == "collect_fields":
        reg.appointment_slot = reg.appointment_token = None
        payload = args.get("patient_payload")
        if not isinstance(payload, dict):
            raise AppError(422, "validation_error", "patient_payload must be an object")
        valid, errors = validate_fields(payload)
        draft, existing_errors = dict(reg.draft), dict(reg.field_errors)
        for key in payload:
            # Never fall back to an old value after an invalid attempted correction.
            draft.pop(key, None)
            existing_errors.pop(key, None)
        draft.update(valid)
        existing_errors.update(errors)
        reg.draft = jsonable_encoder(draft)
        reg.field_errors = existing_errors
        reg.confirmation_token, reg.status = None, "collecting"
        if not reg.update_patient_id and reg.draft.get("phone_number"):
            duplicate = service.lookup(reg.draft["phone_number"])
            if duplicate:
                reg.status = "awaiting_update_permission"
                result = snapshot(reg)
                # Missing draft fields are not missing from the saved patient.
                result.pop("missing_required")
                return result | update_choice(duplicate)
        return snapshot(reg)

    if name == "decline_required_field":
        field = args.get("field")
        if field not in REQUIRED_FIELDS:
            raise AppError(422, "validation_error", "Specify a required field")
        counts = dict(reg.refusals)
        counts[field] = counts.get(field, 0) + 1
        reg.refusals, reg.confirmation_token = counts, None
        reg.draft = {k: v for k, v in reg.draft.items() if k != field}
        if counts[field] >= 2:
            reg.status, reg.draft, reg.field_errors = "cancelled", {}, {}
        return {
            "success": True,
            "end_call": reg.status == "cancelled",
            "message": "Registration cannot be completed"
            if counts[field] >= 2
            else f"{field.replace('_', ' ')} is required; please ask once more",
        }

    if name == "lookup_patient_by_phone":
        patient = service.lookup(args.get("phone_number", ""))
        if patient and not reg.update_patient_id:
            reg.draft = dict(reg.draft) | {"phone_number": patient.phone_number}
            reg.field_errors = {k: v for k, v in reg.field_errors.items() if k != "phone_number"}
            reg.confirmation_token, reg.status = None, "awaiting_update_permission"
            return {"success": True, "found": True} | update_choice(patient)
        return {
            "success": True,
            "found": patient is not None,
            "patient": {
                "patient_id": str(patient.patient_id),
                "first_name": patient.first_name,
                "last_name": patient.last_name,
            }
            if patient
            else None,
        }

    if name == "accept_existing_update":
        if not update_permission(args.get("caller_response")):
            return failed_step(
                reg,
                "_edit_permission_failures",
                "ask_update_permission",
                "Ask one clear question: Would you like to edit your existing record? "
                "WAIT for their answer, then retry accept_existing_update. "
                "Do not prepare confirmation or save until the record is loaded.",
            )
        patient = service.lookup(reg.draft.get("phone_number", ""))
        if not patient or str(patient.patient_id) != args.get("patient_id"):
            raise AppError(404, "not_found", "No matching active patient for the draft phone")
        if reg.update_patient_id == patient.patient_id:
            return snapshot(reg) | {"next_action": "collect_requested_changes"}
        existing = PatientCreate.model_validate(
            PatientRead.model_validate(patient).model_dump(include=set(PatientCreate.model_fields))
        ).model_dump(mode="json")
        existing.update(reg.draft)
        for field in reg.field_errors:
            existing.pop(field, None)
        reg.draft, reg.update_patient_id = existing, patient.patient_id
        reg.confirmation_token, reg.status = None, "collecting"
        return snapshot(reg) | {
            "next_action": "collect_requested_changes",
            "message": "The saved record is now loaded. Keep unchanged fields. Ask only for "
            "the requested corrections or field_errors; do not restart registration. "
            "Read back the final record and obtain fresh confirmation before saving.",
        }

    if name == "prepare_confirmation":
        reg.confirmation_token = None
        if not reg.update_patient_id and reg.draft.get("phone_number"):
            duplicate = service.lookup(reg.draft["phone_number"])
            if duplicate:
                return {"success": False, "error_type": "duplicate_phone"} | update_choice(
                    duplicate
                )
        if args.get("optional_fields_offered") is not True:
            raise AppError(400, "optional_offer_required", "Offer optional fields before read-back")
        if reg.field_errors:
            raise AppError(422, "validation_error", "Resolve invalid fields", reg.field_errors)
        payload = PatientCreate.model_validate(reg.draft)
        duplicate = service.lookup(payload.phone_number)
        if duplicate and duplicate.patient_id != reg.update_patient_id:
            return {
                "success": False,
                "error_type": "duplicate_phone",
                "patient": {
                    "patient_id": str(duplicate.patient_id),
                    "first_name": duplicate.first_name,
                    "last_name": duplicate.last_name,
                },
                "message": "Ask permission to update the existing record, or request another phone",
            }
        reg.draft = payload.model_dump(mode="json")
        reg.confirmation_token, reg.status = str(uuid4()), "awaiting_confirmation"
        return {
            "success": True,
            "confirmation_token": reg.confirmation_token,
            "readback": readback(payload),
            "patient_payload": reg.draft,
            "save_tool": "update_patient" if reg.update_patient_id else "create_patient",
            "patient_id": str(reg.update_patient_id) if reg.update_patient_id else None,
        }

    if name in {"create_patient", "update_patient"}:
        if (
            reg.status != "awaiting_confirmation"
            or not reg.confirmation_token
            or args.get("confirmation_token") != reg.confirmation_token
            or not explicit_confirmation(args.get("caller_response"))
        ):
            duplicate = (
                service.lookup(reg.draft["phone_number"])
                if (not reg.update_patient_id and reg.draft.get("phone_number"))
                else None
            )
            if duplicate:
                result = failed_step(
                    reg,
                    "_save_failures",
                    "accept_existing_update",
                    update_choice(duplicate)["message"],
                )
                if not result.get("end_call"):
                    result["patient"] = update_choice(duplicate)["patient"]
                return result
            if (
                reg.status != "awaiting_confirmation"
                or not reg.confirmation_token
                or (args.get("confirmation_token") != reg.confirmation_token)
            ):
                return failed_step(
                    reg,
                    "_save_failures",
                    "prepare_confirmation",
                    "Do NOT retry save or just ask for another yes. First collect any "
                    "unrecorded corrections, then call prepare_confirmation. WAIT for "
                    "success and its real token; read the returned full record, obtain "
                    "fresh consent, and only then save. Never invent a token.",
                )
            return failed_step(
                reg,
                "_save_failures",
                "ask_final_confirmation",
                "The caller response is not clear final consent. Clarify it. "
                "If a correction was requested, collect it and prepare a fresh read-back.",
            )
        if (name == "update_patient") != bool(reg.update_patient_id):
            raise AppError(
                400, "wrong_operation", "Use the save_tool returned by prepare_confirmation"
            )
        if name == "update_patient" and args.get("patient_id") != str(reg.update_patient_id):
            raise AppError(400, "wrong_patient", "Use the confirmed patient ID")
        payload = PatientCreate.model_validate(reg.draft)
        if settings.log_patient_payload:
            event(
                "patient_registration_confirmed",
                call_id=call_id,
                patient_payload=payload.model_dump(mode="json"),
            )
        patient = (
            service.update(UUID(args["patient_id"]), payload.model_dump())
            if name == "update_patient"
            else service.create(payload)
        )
        reg.status, reg.patient_id, reg.confirmation_token = "saved", patient.patient_id, None
        # Registration may change the selected name/identity after booking preparation.
        # Obtain fresh appointment consent for the saved patient, never reuse that token.
        reg.appointment_slot = reg.appointment_token = reg.booking_patient_id = None
        reg.draft, reg.field_errors, reg.refusals = {}, {}, {}
        # The webhook commits patient and session atomically before delivering this result.
        return {
            "success": True,
            "patient_id": str(patient.patient_id),
            "patient": PatientRead.model_validate(patient).model_dump(mode="json"),
        }
    raise AppError(400, "unknown_tool", "Unknown voice tool")


def validation_result(exc: ValidationError) -> dict:
    return {
        "success": False,
        "error_type": "validation_error",
        "field_errors": {
            ".".join(map(str, error["loc"])): error["msg"]
            for error in exc.errors(include_input=False, include_context=False)
        },
    }
