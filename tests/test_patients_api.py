from uuid import uuid4

import pytest

from app.core.config import settings
from app.models.patient import Patient


def test_crud_filters_timestamps_soft_delete(client, patient, db_factory):
    response = client.post("/patients", json=patient)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert response.json()["error"] is None
    assert data["phone_number"] == "4155550182"
    assert data["state"] == "CA"
    assert data["date_of_birth"] == "1993-06-14"
    assert data["preferred_language"] == "English"
    assert data["created_at"].endswith("Z")
    patient_id = data["patient_id"]
    assert client.get(f"/patients/{patient_id}").json()["data"] == data
    for filters in (
        {},
        {"last_name": "demo"},
        {"date_of_birth": "06/14/1993"},
        {"phone_number": "(415) 555-0182"},
    ):
        assert len(client.get("/patients", params=filters).json()["data"]) == 1
    assert client.get("/patients", params={"last_name": "Nobody"}).json()["data"] == []
    response = client.put(f"/patients/{patient_id}", json={"last_name": "Davis"})
    assert response.status_code == 200
    assert response.json()["data"]["last_name"] == "Davis"
    assert response.json()["data"]["first_name"] == "Jane"
    assert response.json()["data"]["updated_at"] > data["updated_at"]
    assert client.delete(f"/patients/{patient_id}").status_code == 200
    assert client.get(f"/patients/{patient_id}").status_code == 404
    assert client.get("/patients").json()["data"] == []
    from uuid import UUID

    with db_factory() as db:
        row = db.get(Patient, UUID(patient_id))
        assert row is not None and row.deleted_at is not None
    # A deleted record no longer reserves the phone.
    assert client.post("/patients", json=patient).status_code == 201


@pytest.mark.parametrize(
    "field,value",
    [
        ("date_of_birth", "12/31/2999"),
        ("date_of_birth", "02/30/2000"),
        ("date_of_birth", "tomorrow"),
        ("phone_number", "123"),
        ("phone_number", "1111111111"),
        ("zip_code", "1234"),
        ("zip_code", "123456789"),
        ("state", "ZZ"),
        ("email", "not-an-email"),
        ("first_name", "Jane123"),
        ("last_name", ""),
        ("sex", "unknown"),
        ("city", " "),
        ("insurance_member_id", "A-1"),
        ("emergency_contact_phone", "123"),
        ("first_name", None),
        ("preferred_language", None),
    ],
)
def test_invalid_create_and_partial_update(client, patient, field, value):
    created = client.post("/patients", json=patient).json()["data"]
    for response in (
        client.post("/patients", json=patient | {field: value}),
        client.put(f"/patients/{created['patient_id']}", json={field: value}),
    ):
        assert response.status_code == 422, response.text
        assert response.json()["data"] is None
        assert response.json()["error"]["code"] == "validation_error"


def test_unknown_fields_missing_and_null(client, patient):
    assert client.post("/patients", json={"first_name": "Jane"}).status_code == 422
    assert client.post("/patients", json=patient | {"invented": 1}).status_code == 422
    created = client.post("/patients", json=patient | {"email": "demo@example.com"}).json()["data"]
    path = f"/patients/{created['patient_id']}"
    assert client.put(path, json={"invented": "x"}).status_code == 422
    assert client.put(path, json={"email": None}).json()["data"]["email"] is None


def test_duplicates(client, patient):
    assert client.post("/patients", json=patient).status_code == 201
    assert (
        client.post("/patients", json=patient | {"phone_number": "4155550182"}).status_code == 409
    )
    second = client.post("/patients", json=patient | {"phone_number": "4155550100"}).json()["data"]
    assert (
        client.put(
            f"/patients/{second['patient_id']}", json={"phone_number": "4155550182"}
        ).status_code
        == 409
    )


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_and_invalid_uuid(client, method):
    kwargs = {"json": {"last_name": "Demo"}} if method == "put" else {}
    assert getattr(client, method)(f"/patients/{uuid4()}", **kwargs).status_code == 404
    assert getattr(client, method)("/patients/not-a-uuid", **kwargs).status_code == 422


def test_envelopes_docs_health_auth(client, monkeypatch):
    assert client.get("/health").json() == {"data": {"status": "ok"}, "error": None}
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    assert "/voice/vapi" in spec["paths"] and "/patients/{patient_id}" in spec["paths"]
    assert client.get("/missing").json()["data"] is None
    assert client.get("/patients", params={"phone_number": "123"}).status_code == 422
    monkeypatch.setattr(settings, "api_key", "test-api-key")
    assert client.get("/patients").status_code == 401
    assert client.get("/patients", headers={"X-API-Key": "test-api-key"}).status_code == 200


def test_database_failure_is_safe(client, patient, monkeypatch):
    from sqlalchemy.exc import OperationalError

    from app.services.patient_service import PatientService

    def fail(*args):
        raise OperationalError("secret SQL", {}, Exception("private details"))

    monkeypatch.setattr(PatientService, "create", fail)
    response = client.post("/patients", json=patient)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "system_error"
    assert "private details" not in response.text and "secret SQL" not in response.text
