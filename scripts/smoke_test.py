"""Exercise the running REST API using fake data; always attempt soft-delete cleanup."""

import argparse
import secrets
import sys

import httpx

from app.core.config import settings


def fake_patient() -> dict:
    return {
        "first_name": "Demo",
        "last_name": "Smoke",
        "date_of_birth": "01/15/1990",
        "sex": "Decline to Answer",
        "phone_number": f"41555501{secrets.randbelow(100):02d}",
        "address_line_1": "123 Fictional Street",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94105",
        "email": "fake-demo@example.com",
    }


def check(condition: bool, description: str) -> None:
    if not condition:
        raise AssertionError(description)
    print(f"PASS {description}")


def run(base_url: str):
    headers = {"X-API-Key": settings.api_key} if settings.api_key else {}
    patient_id = None
    with httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=20) as client:
        try:
            health = client.get("/health")
            check(
                health.status_code == 200
                and health.json()
                == {
                    "data": {"status": "ok"},
                    "error": None,
                },
                "health and envelope",
            )
            # Avoid overwriting demo records in the reserved fictional 555-0100..0199 range.
            for _ in range(100):
                payload = fake_patient()
                response = client.post("/patients", json=payload)
                if response.status_code != 409:
                    break
            check(response.status_code == 201, "create fake patient")
            patient_id = response.json()["data"]["patient_id"]
            path = f"/patients/{patient_id}"
            check(client.get(path).json()["data"]["patient_id"] == patient_id, "retrieve patient")
            found = client.get("/patients", params={"phone_number": payload["phone_number"]})
            check(any(p["patient_id"] == patient_id for p in found.json()["data"]), "phone search")
            check(
                client.put(path, json={"last_name": "Verified"}).status_code == 200,
                "partial update",
            )
            check(client.get(path).json()["data"]["last_name"] == "Verified", "verify update")
            check(client.delete(path).status_code == 200, "soft delete")
            check(client.get(path).status_code == 404, "deleted patient hidden")
            active = client.get("/patients", params={"phone_number": payload["phone_number"]})
            check(
                not any(p["patient_id"] == patient_id for p in active.json()["data"]),
                "deleted patient absent from search",
            )
        finally:
            if patient_id:
                cleanup = client.delete(f"/patients/{patient_id}")
                if cleanup.status_code not in {200, 404}:
                    raise RuntimeError(f"Cleanup failed for {patient_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        run(args.base_url)
    except (httpx.HTTPError, AssertionError, ValueError, KeyError, RuntimeError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        sys.exit(1)
