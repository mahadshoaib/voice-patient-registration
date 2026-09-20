from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import require_api_key
from app.core.exceptions import AppError
from app.core.logging import event
from app.db.session import get_db
from app.schemas.patient import Envelope, PatientCreate, PatientRead, validate_fields
from app.services.patient_service import PatientService, commit

router = APIRouter(prefix="/patients", tags=["Patients"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=Envelope[list[PatientRead]])
def list_patients(
    last_name: str | None = Query(None),
    date_of_birth: str | None = Query(None, description="MM/DD/YYYY or YYYY-MM-DD"),
    phone_number: str | None = Query(None),
    db: Session = Depends(get_db),
):
    filters, errors = validate_fields(
        {
            k: v
            for k, v in {
                "last_name": last_name,
                "date_of_birth": date_of_birth,
                "phone_number": phone_number,
            }.items()
            if v is not None
        }
    )
    if errors:
        raise AppError(422, "validation_error", "Invalid search parameters", errors)
    return {"data": PatientService(db).repo.list(**filters), "error": None}


@router.get("/{patient_id}", response_model=Envelope[PatientRead])
def get_patient(patient_id: UUID, db: Session = Depends(get_db)):
    return {"data": PatientService(db).get(patient_id), "error": None}


@router.post("", status_code=201, response_model=Envelope[PatientRead])
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    patient = PatientService(db).create(payload)
    commit(db)
    event("patient_created", patient_id=patient.patient_id)
    return {"data": patient, "error": None}


@router.put("/{patient_id}", response_model=Envelope[PatientRead])
def update_patient(
    patient_id: UUID,
    payload: dict = Body(
        ...,
        description=(
            "Partial patient fields. Omitted values stay unchanged; null clears optional fields."
        ),
        examples=[{"last_name": "Davis"}],
    ),
    db: Session = Depends(get_db),
):
    patient = PatientService(db).update(patient_id, payload)
    commit(db)
    event("patient_updated", patient_id=patient.patient_id)
    return {"data": patient, "error": None}


@router.delete("/{patient_id}", response_model=Envelope[dict])
def delete_patient(patient_id: UUID, db: Session = Depends(get_db)):
    patient = PatientService(db).delete(patient_id)
    commit(db)
    return {"data": {"patient_id": patient.patient_id, "deleted": True}, "error": None}
