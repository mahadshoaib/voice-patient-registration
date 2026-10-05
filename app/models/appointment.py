from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utcnow


class Appointment(Base):
    """One shared mock clinic calendar; cancellation releases the slot."""

    __tablename__ = "appointments"
    appointment_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.patient_id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    __table_args__ = (
        Index(
            "uq_appointments_active_slot",
            "starts_at",
            unique=True,
            postgresql_where=text("cancelled_at IS NULL"),
            sqlite_where=text("cancelled_at IS NULL"),
        ),
    )
