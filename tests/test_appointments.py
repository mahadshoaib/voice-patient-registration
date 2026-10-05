from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from test_voice_tools import prepare, save, tool

from app.core.config import settings
from app.models.appointment import Appointment
from app.services.appointment_service import scheduled_slots


def slots(client):
    response = client.get("/appointments/slots")
    assert response.status_code == 200
    return response.json()["data"]["slots"]


def create(client, patient):
    return client.post("/patients", json=patient).json()["data"]["patient_id"]


def test_schedule_is_weekdays_future_and_bounded():
    now = datetime(2026, 10, 5, 14, 0, tzinfo=UTC)
    available = scheduled_slots(now)
    assert available[0] == now + timedelta(minutes=30)
    assert all(s > now and s < now + timedelta(days=14) for s in available)
    assert all(s.weekday() < 5 and 14 <= s.hour < 20 and s.minute in {0, 30} for s in available)


def test_dashboard_public_but_data_protected(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "reviewer-test")
    assert client.get("/dashboard").status_code == 200
    assert client.get("/static/dashboard.js").status_code == 200
    for path in ("/patients", "/appointments", "/appointments/slots"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"X-API-Key": "reviewer-test"}).status_code == 200
    assert client.post("/appointments", json={}).status_code == 401
    assert client.delete("/appointments/00000000-0000-0000-0000-000000000000").status_code == 401


def test_booking_conflict_idempotency_and_cancellation(client, patient):
    first = create(client, patient)
    second = create(client, patient | {"phone_number": "4155550183"})
    slot = slots(client)[0]
    payload = {"patient_id": first, "starts_at": slot}
    booked = client.post("/appointments", json=payload)
    assert booked.status_code == 201
    appointment = booked.json()["data"]
    assert slot not in slots(client)
    assert client.post("/appointments", json=payload).json()["data"] == appointment
    assert client.post("/appointments", json=payload | {"patient_id": second}).status_code == 409
    assert len(client.get("/appointments", params={"patient_id": first}).json()["data"]) == 1
    assert client.get("/appointments", params={"patient_id": second}).json()["data"] == []
    for _ in range(2):
        assert client.delete(f"/appointments/{appointment['appointment_id']}").status_code == 200
    assert slot in slots(client)
    assert client.post("/appointments", json=payload | {"patient_id": second}).status_code == 201


@pytest.mark.parametrize(
    "time", ["2020-01-01T14:00:00Z", "2035-01-01T14:00:00Z", "2026-10-05T14:00:00", "bad"]
)
def test_invalid_times_rejected(client, patient, time):
    patient_id = create(client, patient)
    assert (
        client.post("/appointments", json={"patient_id": patient_id, "starts_at": time}).status_code
        == 422
    )


def test_off_grid_and_deleted_patient_cannot_book(client, patient):
    patient_id = create(client, patient)
    slot = slots(client)[0]
    invalid = datetime.fromisoformat(slot.replace("Z", "+00:00")) + timedelta(minutes=1)
    assert (
        client.post(
            "/appointments", json={"patient_id": patient_id, "starts_at": invalid.isoformat()}
        ).status_code
        == 422
    )
    assert (
        client.post("/appointments", json={"patient_id": patient_id, "starts_at": slot}).status_code
        == 201
    )
    assert client.delete(f"/patients/{patient_id}").status_code == 200
    assert slot in slots(client)
    assert (
        client.post("/appointments", json={"patient_id": patient_id, "starts_at": slot}).status_code
        == 404
    )


def test_database_unique_index_is_final_conflict_guard(client, patient, db_factory):
    from uuid import UUID

    patient_id = UUID(create(client, patient))
    slot = datetime.fromisoformat(slots(client)[0].replace("Z", "+00:00"))
    with db_factory() as db:
        db.add(Appointment(patient_id=patient_id, starts_at=slot))
        db.commit()
    with db_factory() as db:
        db.add(Appointment(patient_id=patient_id, starts_at=slot))
        with pytest.raises(IntegrityError):
            db.commit()


def test_voice_new_patient_booking_after_saved_and_retry(client, patient):
    saved = save(client, prepare(client, patient))
    slot = tool(client, "list_appointment_slots")["slots"][0]
    pending = tool(client, "prepare_appointment", {"starts_at": slot})
    assert pending["success"] and "UTC" in pending["readback"]
    assert client.get("/appointments").json()["data"] == []
    args = {
        "confirmation_token": pending["confirmation_token"],
        "caller_response": "Yes. This is correct.",
    }
    booked = tool(client, "book_appointment", args)
    assert booked["success"]
    assert booked["appointment"]["patient_id"] == saved["patient_id"]
    assert tool(client, "book_appointment", args)["already_booked"]
    assert len(client.get("/appointments").json()["data"]) == 1


def test_voice_returning_booking_identity_and_fresh_consent(client, patient):
    patient_id = create(client, patient)
    slot, second_slot = slots(client)[:2]
    assert not tool(client, "prepare_appointment", {"starts_at": slot})["success"]
    identity = {"phone_number": patient["phone_number"], "date_of_birth": patient["date_of_birth"]}
    assert not tool(
        client, "select_appointment_patient", identity | {"date_of_birth": "01/01/1990"}
    )["success"]
    assert tool(client, "select_appointment_patient", identity)["success"]
    pending = tool(client, "prepare_appointment", {"starts_at": slot})
    updated = tool(client, "prepare_appointment", {"starts_at": second_slot})
    assert not tool(
        client,
        "book_appointment",
        {"confirmation_token": pending["confirmation_token"], "caller_response": "yes"},
    )["success"]
    assert not tool(
        client,
        "book_appointment",
        {
            "confirmation_token": updated["confirmation_token"],
            "caller_response": "yes but another day",
        },
    )["success"]
    result = tool(
        client,
        "book_appointment",
        {"confirmation_token": updated["confirmation_token"], "caller_response": "yes"},
    )
    assert result["success"] and result["appointment"]["patient_id"] == patient_id
    assert client.get(f"/patients/{patient_id}").json()["data"]["phone_number"] == "4155550182"


def test_voice_unavailable_prepare_clears_consent_and_ended_call_blocks(client, patient):
    patient_id = create(client, patient)
    tool(
        client,
        "select_appointment_patient",
        {"phone_number": patient["phone_number"], "date_of_birth": patient["date_of_birth"]},
    )
    slot = slots(client)[0]
    pending = tool(client, "prepare_appointment", {"starts_at": slot})
    client.post("/appointments", json={"patient_id": patient_id, "starts_at": slot})
    assert not tool(client, "prepare_appointment", {"starts_at": slot})["success"]
    assert not tool(
        client,
        "book_appointment",
        {"confirmation_token": pending["confirmation_token"], "caller_response": "yes"},
    )["success"]
    client.post(
        "/voice/vapi",
        headers={"X-Vapi-Secret": "test-webhook-secret"},
        json={"message": {"type": "end-of-call-report", "call": {"id": "test-call"}}},
    )
    assert tool(client, "list_appointment_slots")["error_type"] == "call_closed"


def test_voice_consent_retry_limit_preserves_registration(client, patient):
    saved = save(client, prepare(client, patient))
    for _ in range(3):
        result = tool(
            client, "book_appointment", {"confirmation_token": "dummy", "caller_response": "yes"}
        )
    assert result["end_call"] is True
    assert tool(client, "list_appointment_slots")["error_type"] == "retry_limit_reached"
    assert client.get(f"/patients/{saved['patient_id']}").status_code == 200
    assert client.get("/appointments").json()["data"] == []


def test_invalid_correction_invalidates_booking_consent(client, patient):
    save(client, prepare(client, patient))
    pending = tool(client, "prepare_appointment", {"starts_at": slots(client)[0]})
    assert not tool(client, "prepare_appointment", {"starts_at": "bad"})["success"]
    assert not tool(
        client,
        "book_appointment",
        {"confirmation_token": pending["confirmation_token"], "caller_response": "yes"},
    )["success"]
    assert client.get("/appointments").json()["data"] == []


def test_offset_slot_is_read_back_in_utc(client, patient):
    from datetime import timezone

    save(client, prepare(client, patient))
    slot = datetime.fromisoformat(slots(client)[0].replace("Z", "+00:00"))
    offset = slot.astimezone(timezone(timedelta(hours=5)))
    result = tool(client, "prepare_appointment", {"starts_at": offset.isoformat()})
    assert result["success"]
    assert slot.strftime("%H:%M") + " UTC" in result["readback"]


def test_saved_patient_cannot_be_replaced_for_booking(client, patient):
    saved = save(client, prepare(client, patient))
    second = patient | {"phone_number": "4155550184"}
    create(client, second)
    result = tool(
        client,
        "select_appointment_patient",
        {"phone_number": second["phone_number"], "date_of_birth": second["date_of_birth"]},
    )
    assert result["error_type"] == "patient_already_selected"
    pending = tool(client, "prepare_appointment", {"starts_at": slots(client)[0]})
    booked = tool(
        client,
        "book_appointment",
        {"confirmation_token": pending["confirmation_token"], "caller_response": "yes"},
    )
    assert booked["appointment"]["patient_id"] == saved["patient_id"]
