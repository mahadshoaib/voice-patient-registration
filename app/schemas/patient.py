from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    TypeAdapter,
)

from app.validators import patient as validate

Name = Annotated[str, AfterValidator(validate.name)]
DOB = Annotated[date, BeforeValidator(validate.dob)]
Phone = Annotated[str, AfterValidator(validate.phone)]
State = Annotated[str, AfterValidator(validate.state)]
ZIP = Annotated[str, AfterValidator(validate.zip_code)]
Text100 = Annotated[str, Field(min_length=1, max_length=100)]
Text200 = Annotated[str, Field(min_length=1, max_length=200)]
Sex = Literal["Male", "Female", "Other", "Decline to Answer"]


class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    first_name: Name = Field(examples=["Jane"])
    last_name: Name = Field(examples=["Demo"])
    date_of_birth: DOB = Field(description="MM/DD/YYYY or YYYY-MM-DD; not in the future")
    sex: Sex
    phone_number: Phone = Field(examples=["415-555-0182"])
    email: Annotated[EmailStr, Field(max_length=254)] | None = None
    address_line_1: Text200
    address_line_2: Text200 | None = None
    city: Text100
    state: State
    zip_code: ZIP
    insurance_provider: Text200 | None = None
    insurance_member_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9]{1,100}$")] | None = None
    preferred_language: Text100 = "English"
    emergency_contact_name: Text100 | None = None
    emergency_contact_phone: Phone | None = None


REQUIRED_FIELDS = {k for k, field in PatientCreate.model_fields.items() if field.is_required()}
ADAPTERS = {
    key: TypeAdapter(field.rebuild_annotation())
    for key, field in PatientCreate.model_fields.items()
}


def validate_fields(payload: dict) -> tuple[dict, dict]:
    """Validate each supplied field independently; used for partial updates and voice drafts."""
    from pydantic import ValidationError

    valid, errors = {}, {}
    for key, value in payload.items():
        if key not in ADAPTERS:
            errors[key] = "Unknown patient field"
            continue
        try:
            value = value.strip() if isinstance(value, str) else value
            valid[key] = ADAPTERS[key].validate_python(value)
        except ValidationError as exc:
            errors[key] = exc.errors(include_input=False, include_context=False)[0]["msg"]
    return valid, errors


class PatientRead(PatientCreate):
    model_config = ConfigDict(from_attributes=True)
    patient_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: object | None = None


class Envelope[T](BaseModel):
    data: T | None = None
    error: ErrorInfo | None = None
