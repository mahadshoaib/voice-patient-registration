from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_api_key
from app.db.session import get_db
from app.schemas.appointment import AppointmentCreate, AppointmentRead, ScheduleRead
from app.schemas.patient import Envelope
from app.services.appointment_service import SCHEDULE, AppointmentService
from app.services.patient_service import commit

router = APIRouter(
    prefix="/appointments", tags=["Appointments"], dependencies=[Depends(require_api_key)]
)


@router.get("/slots", response_model=Envelope[ScheduleRead])
def available_slots(db: Session = Depends(get_db)):
    return {"data": {"description": SCHEDULE, "slots": AppointmentService(db).slots()}}


@router.get("", response_model=Envelope[list[AppointmentRead]])
def list_appointments(patient_id: UUID | None = None, db: Session = Depends(get_db)):
    return {"data": AppointmentService(db).list(patient_id)}


@router.post("", status_code=201, response_model=Envelope[AppointmentRead])
def book_appointment(payload: AppointmentCreate, db: Session = Depends(get_db)):
    appointment = AppointmentService(db).book(payload.patient_id, payload.starts_at)
    commit(db)
    return {"data": appointment}


@router.delete("/{appointment_id}", response_model=Envelope[AppointmentRead])
def cancel_appointment(appointment_id: UUID, db: Session = Depends(get_db)):
    appointment = AppointmentService(db).cancel(appointment_id)
    commit(db)
    return {"data": appointment}
