from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.base import utcnow
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientCreate, validate_fields
from app.validators.patient import phone


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PatientRepository(db)

    def get(self, patient_id: UUID) -> Patient:
        patient = self.repo.get(patient_id)
        if patient is None:
            raise AppError(404, "not_found", "Patient not found")
        return patient

    def lookup(self, phone_number: str) -> Patient | None:
        return self.repo.by_phone(phone(phone_number))

    def create(self, payload: PatientCreate) -> Patient:
        if self.repo.by_phone(payload.phone_number):
            raise AppError(
                409, "duplicate_phone", "An active record already uses this phone number"
            )
        patient = Patient(**payload.model_dump())
        self.db.add(patient)
        self.db.flush()
        return patient

    def update(self, patient_id: UUID, payload: dict) -> Patient:
        patient = self.get(patient_id)
        valid, errors = validate_fields(payload)
        if errors:
            raise AppError(422, "validation_error", "Please correct the specified fields", errors)
        # Validate the merged object, including required/null invariants.
        merged = {key: getattr(patient, key) for key in PatientCreate.model_fields}
        merged.update(valid)
        checked = PatientCreate.model_validate(merged)
        duplicate = self.repo.by_phone(checked.phone_number)
        if duplicate and duplicate.patient_id != patient_id:
            raise AppError(
                409, "duplicate_phone", "An active record already uses this phone number"
            )
        for key in valid:
            setattr(patient, key, getattr(checked, key))
        if valid:
            patient.updated_at = utcnow()
        self.db.flush()
        return patient

    def delete(self, patient_id: UUID) -> Patient:
        patient = self.get(patient_id)
        patient.deleted_at = utcnow()
        patient.updated_at = patient.deleted_at
        self.db.flush()
        return patient


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "conflict", "A conflicting record already exists") from None
