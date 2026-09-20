from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utcnow


class Registration(Base):
    """Durable call draft. A draft is never an active patient."""

    __tablename__ = "registrations"
    call_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    draft: Mapped[dict] = mapped_column(JSON, default=dict)
    field_errors: Mapped[dict] = mapped_column(JSON, default=dict)
    refusals: Mapped[dict] = mapped_column(JSON, default=dict)
    confirmation_token: Mapped[str | None] = mapped_column(String(36))
    update_patient_id: Mapped[UUID | None] = mapped_column(Uuid)
    patient_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(30), default="collecting")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    __mapper_args__ = {"version_id_col": version}
