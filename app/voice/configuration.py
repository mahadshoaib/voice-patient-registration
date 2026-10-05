from pathlib import Path

from app.core.config import Settings
from app.schemas.patient import PatientCreate


def assistant_configuration(settings: Settings) -> dict:
    server = {
        "url": settings.public_base_url.rstrip("/") + "/voice/vapi",
        "headers": {"X-Vapi-Secret": settings.vapi_webhook_secret},
        "timeoutSeconds": 20,
    }
    patient_schema = PatientCreate.model_json_schema()
    # Dates accept MM/DD/YYYY as well as ISO: do not constrain the LLM to JSON date format.
    patient_schema["properties"]["date_of_birth"].pop("format", None)
    string = {"type": "string"}
    definitions = [
        (
            "select_appointment_patient",
            "For a returning caller who only wants booking: match registered phone and DOB. "
            "Does not change demographics. New patients must finish registration first.",
            {"phone_number": string, "date_of_birth": string},
            ["phone_number", "date_of_birth"],
        ),
        (
            "list_appointment_slots",
            "Fetch real availability from the MOCK clinic database. Optional date YYYY-MM-DD. "
            "Returns up to six times plus available dates. Never invent availability.",
            {"date": string},
            [],
        ),
        (
            "prepare_appointment",
            "Select an available starts_at ISO timestamp returned by list_appointment_slots. "
            "Returns readback and token, does NOT book. Read back, then WAIT for consent.",
            {"starts_at": string},
            ["starts_at"],
        ),
        (
            "book_appointment",
            "Book ONLY after the prepared appointment was read back and the caller confirmed. "
            "Pass exact reply and token. Wait for success before announcing booking.",
            {"confirmation_token": string, "caller_response": string},
            ["confirmation_token", "caller_response"],
        ),
        (
            "collect_fields",
            "Validate and merge all demographics from the latest caller utterance. "
            "Also use for corrections. Does NOT save a patient.",
            {
                "patient_payload": {
                    "type": "object",
                    "properties": patient_schema["properties"],
                    "additionalProperties": False,
                }
            },
            ["patient_payload"],
        ),
        ("start_over", "Clear all data collected in this call and begin again.", {}, []),
        (
            "decline_required_field",
            "Record a refusal; ask once more, end on second refusal.",
            {"field": string},
            ["field"],
        ),
        (
            "lookup_patient_by_phone",
            "Find a returning patient's record by phone before asking other demographics. "
            "If found, obtain update permission and immediately call accept_existing_update.",
            {"phone_number": string},
            ["phone_number"],
        ),
        (
            "accept_existing_update",
            "REQUIRED immediately after caller agrees to update an existing record. "
            "Loads all saved demographics into the draft so only changes need to be asked. "
            "Pass their exact reply, including requests such as I want to update my name. "
            "Does not save; separate final read-back confirmation is still required.",
            {"patient_id": string, "caller_response": string},
            ["patient_id", "caller_response"],
        ),
        (
            "prepare_confirmation",
            "Validate complete draft and return the full read-back and token. "
            "Read it aloud and WAIT for explicit caller consent. Does NOT save.",
            {"optional_fields_offered": {"type": "boolean"}},
            ["optional_fields_offered"],
        ),
        (
            "create_patient",
            "Save current validated draft ONLY after reading it back and receiving "
            "explicit caller confirmation. Wait for success before announcing registration.",
            {"confirmation_token": string, "caller_response": string},
            ["confirmation_token", "caller_response"],
        ),
        (
            "update_patient",
            "Update the selected duplicate record ONLY after fresh read-back "
            "and explicit caller confirmation.",
            {"patient_id": string, "confirmation_token": string, "caller_response": string},
            ["patient_id", "confirmation_token", "caller_response"],
        ),
    ]
    tools = [
        {
            "type": "function",
            "async": False,
            # Explicitly suppress Vapi's default per-tool filler messages.
            "messages": [
                {
                    "type": "request-start",
                    "content": "I'm saving your registration now."
                    if name in {"create_patient", "update_patient"}
                    else "",
                    "blocking": name in {"create_patient", "update_patient"},
                }
            ],
            "server": server,
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        }
        for name, description, properties, required in definitions
    ]
    for tool in tools:
        if tool["function"]["name"] in {"create_patient", "update_patient"}:
            tool["messages"].append(
                {
                    "type": "request-complete",
                    "role": "system",
                    "content": "The save request has returned. Read its actual result now. "
                    "Only if success=true, say: Your registration has been saved. "
                    "Then ask whether they would like a demonstration appointment. "
                    "If yes, use list_appointment_slots; if no, thank them and endCall. "
                    "If success=false, do not announce success or use a farewell; follow "
                    "next_action, or explain the failure. If end_call=true, explain nothing "
                    "was saved and call endCall. Never treat HTTP completion as save success.",
                }
            )
        if tool["function"]["name"] == "book_appointment":
            tool["messages"].append(
                {
                    "type": "request-complete",
                    "role": "system",
                    "content": "Read the actual booking result. Only after success=true, confirm "
                    "the appointment date and UTC time, thank the caller, then endCall. "
                    "If success=false, do not announce a booking. Refresh unavailable slots; "
                    "follow next_action. Never equate HTTP completion with success.",
                }
            )
    tools.append({"type": "endCall"})
    return {
        "name": "Patient Registration",
        "firstMessage": "Thank you for calling patient registration. "
        "I'll help you get registered today. May I have your first and last name, please?",
        "model": {
            "provider": "openai",
            "model": settings.llm_model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        Path(__file__).parent / "prompts/patient_registration_system.md"
                    ).read_text(encoding="utf-8"),
                }
            ],
            "tools": tools,
        },
        "voice": {"provider": "vapi", "voiceId": settings.vapi_voice_id},
        "transcriber": {"provider": "deepgram", "model": "nova-2", "language": "en"},
        "server": server,
        "serverMessages": ["tool-calls", "status-update", "end-of-call-report"],
        "artifactPlan": {"recordingEnabled": False},
        "maxDurationSeconds": 1800,
    }
