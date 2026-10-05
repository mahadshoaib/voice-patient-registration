from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.base import utcnow
from app.models.appointment import Appointment
from app.services.patient_service import PatientService

SCHEDULE = "Mock clinic: Monday–Friday, 14:00–20:00 UTC, 30-minute visits, next 14 days."


def scheduled_slots(now: datetime) -> list[datetime]:
    """UTC intentionally avoids implicit local-time/DST conversions in this demo."""
    midnight = datetime.combine(now.date(), time(), tzinfo=UTC)
    return [
        slot
        for day in range(14)
        for half_hour in range(28, 40)
        if (slot := midnight + timedelta(days=day, minutes=half_hour * 30)).weekday() < 5
        and slot > now
    ]


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db

    def slots(self) -> list[datetime]:
        candidates = scheduled_slots(utcnow())
        taken = set(
            self.db.scalars(
                select(Appointment.starts_at).where(
                    Appointment.cancelled_at.is_(None), Appointment.starts_at.in_(candidates)
                )
            )
        )
        return [slot for slot in candidates if slot not in taken]

    def list(self, patient_id: UUID | None = None) -> list[Appointment]:
        query = select(Appointment).order_by(Appointment.starts_at)
        if patient_id is not None:
            PatientService(self.db).get(patient_id)
            query = query.where(Appointment.patient_id == patient_id)
        return list(self.db.scalars(query))

    def book(self, patient_id: UUID, starts_at: datetime) -> Appointment:
        # Serialize booking against patient deletion too; the unique index is the
        # final arbiter when different patients concurrently choose the same slot.
        from app.models.patient import Patient

        patient = self.db.scalar(
            select(Patient)
            .where(Patient.patient_id == patient_id, Patient.deleted_at.is_(None))
            .with_for_update()
        )
        if patient is None:
            raise AppError(404, "not_found", "Patient not found")
        existing = self.db.scalar(
            select(Appointment).where(
                Appointment.starts_at == starts_at, Appointment.cancelled_at.is_(None)
            )
        )
        if existing:
            if existing.patient_id == patient_id:
                return existing  # Idempotent retry; never create a second booking.
            raise AppError(409, "slot_unavailable", "This slot was taken; refresh availability")
        if starts_at.astimezone(UTC) not in scheduled_slots(utcnow()):
            raise AppError(422, "invalid_slot", "Choose a future time from available slots")
        appointment = Appointment(patient_id=patient_id, starts_at=starts_at.astimezone(UTC))
        self.db.add(appointment)
        self.db.flush()
        return appointment

    def cancel(self, appointment_id: UUID) -> Appointment:
        appointment = self.db.get(Appointment, appointment_id)
        if appointment is None:
            raise AppError(404, "not_found", "Appointment not found")
        if appointment.cancelled_at is None:
            appointment.cancelled_at = utcnow()
            self.db.flush()
        return appointment
