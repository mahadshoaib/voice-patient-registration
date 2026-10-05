from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.schemas.patient import DOB, Phone


class BookingIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone_number: Phone
    date_of_birth: DOB


class AppointmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: UUID
    starts_at: AwareDatetime


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    appointment_id: UUID
    patient_id: UUID
    starts_at: datetime
    created_at: datetime
    cancelled_at: datetime | None


class AppointmentSlot(BaseModel):
    starts_at: AwareDatetime


class ScheduleRead(BaseModel):
    timezone: str = "UTC"
    duration_minutes: int = 30
    description: str
    slots: list[datetime]
