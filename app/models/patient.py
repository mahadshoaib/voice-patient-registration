from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utcnow


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("length(first_name) BETWEEN 1 AND 50", name="ck_first_name"),
        CheckConstraint("length(last_name) BETWEEN 1 AND 50", name="ck_last_name"),
        CheckConstraint("length(phone_number) = 10", name="ck_phone_length"),
        CheckConstraint("length(state) = 2", name="ck_state_length"),
        CheckConstraint("length(zip_code) IN (5, 10)", name="ck_zip_length"),
        CheckConstraint("length(city) BETWEEN 1 AND 100", name="ck_city"),
        CheckConstraint("length(address_line_1) BETWEEN 1 AND 200", name="ck_address"),
        CheckConstraint("sex IN ('Male', 'Female', 'Other', 'Decline to Answer')", name="ck_sex"),
        Index(
            "uq_active_phone",
            "phone_number",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
    patient_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50), index=True)
    date_of_birth: Mapped[date] = mapped_column(Date, index=True)
    sex: Mapped[str] = mapped_column(String(20))
    phone_number: Mapped[str] = mapped_column(String(10), index=True)
    email: Mapped[str | None] = mapped_column(String(254))
    address_line_1: Mapped[str] = mapped_column(String(200))
    address_line_2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    zip_code: Mapped[str] = mapped_column(String(10))
    insurance_provider: Mapped[str | None] = mapped_column(String(200))
    insurance_member_id: Mapped[str | None] = mapped_column(String(100))
    preferred_language: Mapped[str] = mapped_column(String(100), default="English")
    emergency_contact_name: Mapped[str | None] = mapped_column(String(100))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
