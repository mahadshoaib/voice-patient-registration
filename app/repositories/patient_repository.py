from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.patient import Patient


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, patient_id: UUID) -> Patient | None:
        return self.db.scalar(
            select(Patient).where(Patient.patient_id == patient_id, Patient.deleted_at.is_(None))
        )

    def list(self, *, last_name=None, date_of_birth=None, phone_number=None) -> list[Patient]:
        query = select(Patient).where(Patient.deleted_at.is_(None))
        if last_name is not None:
            query = query.where(func.lower(Patient.last_name) == last_name.lower())
        if date_of_birth is not None:
            query = query.where(Patient.date_of_birth == date_of_birth)
        if phone_number is not None:
            query = query.where(Patient.phone_number == phone_number)
        return list(self.db.scalars(query.order_by(Patient.created_at, Patient.patient_id)))

    def by_phone(self, phone: str) -> Patient | None:
        return self.db.scalar(
            select(Patient).where(Patient.phone_number == phone, Patient.deleted_at.is_(None))
        )
