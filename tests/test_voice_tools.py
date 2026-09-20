import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.patient import Patient
from app.models.registration import Registration

OPTIONAL_HISTORY = [
    {
        "role": "bot",
        "message": "Would you like to add email, insurance, an emergency contact, "
        "an apartment or unit, or a preferred language?",
    },
    {"role": "user", "message": "No, thank you."},
]


def tool(client, name, args=None, call_id="test-call", string_args=False, history=None):
    args = args or {}
    response = client.post(
        "/voice/vapi",
        headers={"X-Vapi-Secret": "test-webhook-secret"},
        json={
            "message": {
                "type": "tool-calls",
                "call": {"id": call_id},
                "artifact": {"messages": OPTIONAL_HISTORY if history is None else history},
                "toolCallList": [
                    {
                        "id": "tool_" + str(uuid4()),
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(args) if string_args else args,
                        },
                    }
                ],
            },
        },
    )
    assert response.status_code == 200, response.text
    return json.loads(response.json()["results"][0]["result"])


def prepare(client, patient, call_id="test-call"):
    assert tool(client, "collect_fields", {"patient_payload": patient}, call_id)["success"]
    return tool(client, "prepare_confirmation", {"optional_fields_offered": True}, call_id)


def save(client, prepared, call_id="test-call", response="yes"):
    return tool(
        client,
        prepared["save_tool"],
        {
            "confirmation_token": prepared["confirmation_token"],
            "caller_response": response,
            "patient_id": prepared.get("patient_id"),
        },
        call_id,
    )


def test_confirmed_create_and_retry(client, patient, db_factory):
    prepared = prepare(client, patient)
    assert "June 14, 1993" in prepared["readback"]
    assert client.get("/patients").json()["data"] == []
    saved = save(client, prepared)
    assert saved["success"] and saved["patient"]["last_name"] == "Demo"
    assert save(client, prepared)["patient_id"] == saved["patient_id"]
    assert len(client.get("/patients").json()["data"]) == 1
    with db_factory() as db:
        assert db.get(Registration, "test-call").draft == {}


@pytest.mark.parametrize(
    "response",
    [
        "maybe",
        "no",
        "yes but the address is wrong",
        "",
        True,
        "Yes. This is correct, except my address.",
        "Yes, don't save yet.",
        "Yes? No.",
        "Yes, I guess",
        "Yes. Change my name.",
    ],
)
def test_no_ambiguous_consent(client, patient, response):
    prepared = prepare(client, patient)
    assert save(client, prepared, response=response)["error_type"] == "confirmation_required"
    assert client.get("/patients").json()["data"] == []


@pytest.mark.parametrize(
    "response",
    [
        "Yes. This is correct.",
        "Yes, that's correct!",
        "Yes, that’s right.",
        "  YES! Everything is correct.  ",
        "That is correct.",
    ],
)
def test_natural_confirmation_saves_once(client, patient, response):
    prepared = prepare(client, patient)
    assert save(client, prepared, response=response)["success"]
    assert save(client, prepared, response=response)["already_saved"]
    assert len(client.get("/patients").json()["data"]) == 1


@pytest.mark.parametrize(
    "history",
    [
        [],
        OPTIONAL_HISTORY[:1],
        [{"role": "user", "message": "Yes."}],
        [
            {"role": "bot", "message": "What is your ZIP code?"},
            {"role": "user", "message": "98101"},
        ],
        OPTIONAL_HISTORY[:1] + [{"role": "user", "message": "Say that again."}],
        OPTIONAL_HISTORY
        + [{"role": "tool_calls", "toolCalls": [{"function": {"name": "start_over"}}]}],
    ],
)
def test_optional_offer_cannot_be_faked_with_boolean(client, patient, history):
    tool(client, "collect_fields", {"patient_payload": patient})
    result = tool(
        client, "prepare_confirmation", {"optional_fields_offered": True}, history=history
    )
    assert result["error_type"] == "optional_offer_required"
    assert "confirmation_token" not in result
    assert client.get("/patients").json()["data"] == []


def test_optional_addition_is_in_readback_and_saved(client, patient):
    tool(client, "collect_fields", {"patient_payload": patient})
    history = OPTIONAL_HISTORY[:1] + [{"role": "user", "message": "Add demo@example.com."}]
    tool(client, "collect_fields", {"patient_payload": {"email": "demo@example.com"}})
    prepared = tool(
        client, "prepare_confirmation", {"optional_fields_offered": True}, history=history
    )
    assert "demo@example.com" in prepared["readback"]
    assert save(client, prepared)["patient"]["email"] == "demo@example.com"


def test_cannot_skip_readback(client, patient):
    tool(client, "collect_fields", {"patient_payload": patient})
    result = tool(
        client, "create_patient", {"caller_response": "yes", "confirmation_token": "fake"}
    )
    assert result["error_type"] == "confirmation_required"
    assert tool(client, "prepare_confirmation", {})["error_type"] == "optional_offer_required"


def test_out_of_order_and_correction(client, patient):
    first = tool(
        client,
        "collect_fields",
        {
            "patient_payload": {
                "phone_number": patient["phone_number"],
                "date_of_birth": patient["date_of_birth"],
                "first_name": "Sarah",
                "last_name": "Connor",
            }
        },
        string_args=True,
    )
    assert "phone_number" not in first["missing_required"]
    assert first["draft"]["date_of_birth"] == "1993-06-14"
    rest = {k: v for k, v in patient.items() if k not in first["draft"]}
    tool(client, "collect_fields", {"patient_payload": rest})
    prepared = tool(client, "prepare_confirmation", {"optional_fields_offered": True})
    tool(client, "collect_fields", {"patient_payload": {"last_name": "Davis"}})
    assert save(client, prepared)["error_type"] == "confirmation_required"
    corrected = tool(client, "prepare_confirmation", {"optional_fields_offered": True})
    assert "Sarah Davis" in corrected["readback"]
    assert save(client, corrected)["patient"]["last_name"] == "Davis"


def test_invalid_correction_never_reuses_old_value(client, patient):
    prepared = prepare(client, patient)
    result = tool(
        client,
        "collect_fields",
        {
            "patient_payload": {
                "phone_number": "123",
                "date_of_birth": "01/01/2999",
                "city": "Oakland",
            }
        },
    )
    assert set(result["field_errors"]) == {"phone_number", "date_of_birth"}
    assert result["draft"]["city"] == "Oakland"
    assert "phone_number" not in result["draft"]
    assert save(client, prepared)["error_type"] == "confirmation_required"
    assert (
        tool(client, "prepare_confirmation", {"optional_fields_offered": True})["error_type"]
        == "validation_error"
    )


def test_start_over_clears_all_and_invalidates_token(client, patient):
    prepared = prepare(client, patient | {"email": "demo@example.com"})
    result = tool(client, "start_over")
    assert result["draft"] == {}
    assert len(result["missing_required"]) == 9
    assert save(client, prepared)["error_type"] == "confirmation_required"


def test_duplicate_update_requires_permission_and_reconfirmation(client, patient):
    original = client.post("/patients", json=patient).json()["data"]
    lookup = tool(client, "lookup_patient_by_phone", {"phone_number": "+1 (415) 555-0182"})
    assert lookup["found"] and lookup["patient"]["patient_id"] == original["patient_id"]
    duplicate = prepare(client, patient | {"last_name": "Davis"})
    assert duplicate["error_type"] == "duplicate_phone"
    assert (
        tool(
            client,
            "accept_existing_update",
            {
                "patient_id": original["patient_id"],
                "caller_response": "no",
            },
        )["error_type"]
        == "confirmation_required"
    )
    assert client.get(f"/patients/{original['patient_id']}").json()["data"]["last_name"] == "Demo"
    accepted = tool(
        client,
        "accept_existing_update",
        {
            "patient_id": original["patient_id"],
            "caller_response": "yes",
        },
    )
    assert accepted["success"]
    prepared = tool(client, "prepare_confirmation", {"optional_fields_offered": True})
    assert prepared["save_tool"] == "update_patient"
    saved = save(client, prepared)
    assert saved["patient_id"] == original["patient_id"]
    assert saved["patient"]["last_name"] == "Davis"
    assert len(client.get("/patients").json()["data"]) == 1


def test_refuse_required_twice(client):
    assert not tool(client, "decline_required_field", {"field": "date_of_birth"})["end_call"]
    assert tool(client, "decline_required_field", {"field": "date_of_birth"})["end_call"]
    assert tool(client, "create_patient", {})["error_type"] == "call_closed"


@pytest.mark.parametrize(
    "changes",
    [
        {"first_name": "Anne-Marie", "last_name": "O'Neil"},
        {"date_of_birth": "1988-02-29", "sex": "Decline to Answer"},
        {"phone_number": "6175550136"},
        {
            "address_line_1": "789 Example Lane",
            "address_line_2": "Unit 3A",
            "city": "Boston",
            "state": "MA",
            "zip_code": "02108",
        },
        {"insurance_provider": "Example Health", "insurance_member_id": "TEST628403"},
        {"emergency_contact_name": "Jordan Bennett", "emergency_contact_phone": "6175550184"},
        {"email": "olivia.bennett@example.com", "preferred_language": "Spanish"},
        {
            "email": None,
            "address_line_2": None,
            "insurance_provider": None,
            "insurance_member_id": None,
            "emergency_contact_name": None,
            "emergency_contact_phone": None,
        },
    ],
)
def test_returning_update_all_field_groups(client, patient, changes):
    original = client.post(
        "/patients",
        json=patient
        | {
            "email": "before@example.com",
            "address_line_2": "Unit 1",
            "insurance_provider": "Old Example",
            "insurance_member_id": "OLD123",
            "emergency_contact_name": "Example Contact",
            "emergency_contact_phone": "2065550199",
        },
    ).json()["data"]
    tool(client, "lookup_patient_by_phone", {"phone_number": patient["phone_number"]})
    assert tool(
        client,
        "accept_existing_update",
        {
            "patient_id": original["patient_id"],
            "caller_response": "Please edit my information",
        },
    )["success"]
    assert tool(client, "collect_fields", {"patient_payload": changes})["success"]
    prepared = tool(client, "prepare_confirmation", {"optional_fields_offered": True})
    assert client.get(f"/patients/{original['patient_id']}").json()["data"] == original
    updated = save(client, prepared)["patient"]
    for field, value in original.items():
        if field != "updated_at":
            assert updated[field] == changes.get(field, value)
    assert len(client.get("/patients").json()["data"]) == 1


def test_email_addition_recovers_from_fake_token(client, patient):
    original = client.post("/patients", json=patient).json()["data"]
    tool(client, "lookup_patient_by_phone", {"phone_number": patient["phone_number"]})
    args = {
        "patient_id": original["patient_id"],
        "caller_response": "Yes.",
        "confirmation_token": "dummy",
    }
    assert tool(client, "update_patient", args)["next_action"] == "accept_existing_update"
    loaded = tool(
        client,
        "accept_existing_update",
        {
            "patient_id": original["patient_id"],
            "caller_response": "Yes. I want to add my email.",
        },
    )
    assert loaded["success"] and loaded["missing_required"] == []
    tool(client, "collect_fields", {"patient_payload": {"email": "taniel.bro0ks@example.com"}})
    tool(client, "collect_fields", {"patient_payload": {"email": "daniel.brooks@example.com"}})
    assert tool(client, "update_patient", args)["next_action"] == "prepare_confirmation"
    prepared = tool(client, "prepare_confirmation", {"optional_fields_offered": True})
    assert "daniel.brooks@example.com" in prepared["readback"]
    saved = save(client, prepared, response="Yes. Uh, this is correct now.")
    assert saved["success"] and saved["patient"]["email"] == "daniel.brooks@example.com"
    assert saved["patient_id"] == original["patient_id"]


def test_repeated_fake_tokens_cancel_without_writing(client, patient):
    prepared = prepare(client, patient)
    for attempt in range(3):
        result = tool(
            client,
            "create_patient",
            {
                "confirmation_token": "dummy",
                "caller_response": "yes",
            },
        )
        assert not result["success"]
        if attempt < 2:
            assert result["next_action"] == "prepare_confirmation"
    assert result["error_type"] == "retry_limit_reached" and result["end_call"]
    assert save(client, prepared)["error_type"] == "call_closed"
    assert tool(client, "start_over")["end_call"]
    assert client.get("/patients").json()["data"] == []


def test_repeated_unclear_edit_permission_ends_without_update(client, patient):
    original = client.post("/patients", json=patient).json()["data"]
    tool(client, "lookup_patient_by_phone", {"phone_number": patient["phone_number"]})
    for _ in range(3):
        result = tool(
            client,
            "accept_existing_update",
            {
                "patient_id": original["patient_id"],
                "caller_response": "Maybe later",
            },
        )
    assert result["end_call"] and result["next_action"] == "endCall"
    assert client.get(f"/patients/{original['patient_id']}").json()["data"] == original


def test_returning_patient_loads_before_name_only_edit(client, patient):
    original = client.post("/patients", json=patient).json()["data"]
    lookup = tool(client, "lookup_patient_by_phone", {"phone_number": patient["phone_number"]})
    assert lookup["next_action"] == "accept_existing_update"
    # Reproduce the missed load: corrections must lead back to loading, not intake.
    pending = tool(client, "collect_fields", {"patient_payload": {"last_name": "Shoaib"}})
    assert pending["status"] == "awaiting_update_permission"
    assert "missing_required" not in pending
    assert pending["next_action"] == "accept_existing_update"
    reply = "Yes. I think you have a my name spelling incorrect. I want to update that."
    loaded = tool(
        client,
        "accept_existing_update",
        {
            "patient_id": original["patient_id"],
            "caller_response": reply,
        },
    )
    assert loaded["success"] and loaded["missing_required"] == []
    assert loaded["draft"]["last_name"] == "Shoaib"
    for field in ("date_of_birth", "sex", "address_line_1", "city", "state", "zip_code"):
        assert loaded["draft"][field] == original[field]
    prepared = tool(client, "prepare_confirmation", {"optional_fields_offered": True})
    assert save(client, prepared, response=reply)["error_type"] == "confirmation_required"
    assert client.get(f"/patients/{original['patient_id']}").json()["data"] == original
    saved = save(client, prepared, response="Yes. This is correct.")["patient"]
    assert saved["patient_id"] == original["patient_id"]
    assert saved["created_at"] == original["created_at"]
    assert saved["last_name"] == "Shoaib"
    assert len(client.get("/patients").json()["data"]) == 1


@pytest.mark.parametrize(
    "reply", ["No, I don't want to update", "Maybe later", "Please don't change it"]
)
def test_returning_patient_does_not_load_without_permission(client, patient, reply):
    original = client.post("/patients", json=patient).json()["data"]
    tool(client, "lookup_patient_by_phone", {"phone_number": patient["phone_number"]})
    result = tool(
        client,
        "accept_existing_update",
        {
            "patient_id": original["patient_id"],
            "caller_response": reply,
        },
    )
    assert result["error_type"] == "confirmation_required"
    assert "draft" not in result


def test_load_does_not_restore_invalid_correction(client, patient):
    original = client.post("/patients", json=patient).json()["data"]
    tool(client, "lookup_patient_by_phone", {"phone_number": patient["phone_number"]})
    tool(client, "collect_fields", {"patient_payload": {"date_of_birth": "01/01/2999"}})
    loaded = tool(
        client,
        "accept_existing_update",
        {
            "patient_id": original["patient_id"],
            "caller_response": "Please update my birth date",
        },
    )
    assert "date_of_birth" in loaded["field_errors"]
    assert "date_of_birth" not in loaded["draft"]


def test_dropped_call_no_patient_and_no_late_save(client, patient, db_factory):
    prepared = prepare(client, patient)
    response = client.post(
        "/voice/vapi",
        headers={"X-Vapi-Secret": "test-webhook-secret"},
        json={
            "message": {"type": "end-of-call-report", "call": {"id": "test-call"}},
        },
    )
    assert response.status_code == 200
    assert save(client, prepared)["error_type"] == "call_closed"
    with db_factory() as db:
        assert db.scalar(select(func.count()).select_from(Patient)) == 0
        assert db.get(Registration, "test-call").draft == {}


def test_write_failure_is_not_success_and_rolls_back(client, patient, db_factory, monkeypatch):
    from sqlalchemy.exc import OperationalError

    prepared = prepare(client, patient)
    original_commit = db_factory.class_.commit

    def fail_commit(self):
        raise OperationalError("fake", {}, Exception("simulated outage"))

    monkeypatch.setattr(db_factory.class_, "commit", fail_commit)
    result = save(client, prepared)
    assert not result["success"] and result["error_type"] == "system_error"
    monkeypatch.setattr(db_factory.class_, "commit", original_commit)
    assert client.get("/patients").json()["data"] == []
    assert save(client, prepared)["success"]


def test_webhook_auth_and_malformed_payloads(client):
    assert client.post("/voice/vapi", json={}).status_code == 401
    headers = {"X-Vapi-Secret": "test-webhook-secret"}
    assert client.post("/voice/vapi", headers=headers, json={}).status_code == 422
    assert tool(client, "invented_tool")["error_type"] == "unknown_tool"
    assert tool(client, "collect_fields", {"patient_payload": {"phone_number": "123"}})[
        "field_errors"
    ]["phone_number"]


def test_call_isolation_and_missing_fields(client, patient):
    prepare(client, patient, "call-one")
    other = tool(client, "prepare_confirmation", {"optional_fields_offered": True}, "call-two")
    assert other["error_type"] == "validation_error"
    assert "first_name" in other["field_errors"]
