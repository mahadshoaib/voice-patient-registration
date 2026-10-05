"""Booking tools share the REST service and bind consent to one slot and patient."""

from datetime import UTC, date
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.appointment import Appointment
from app.models.registration import Registration
from app.schemas.appointment import AppointmentRead, AppointmentSlot, BookingIdentity
from app.services.appointment_service import SCHEDULE, AppointmentService
from app.services.patient_service import PatientService

BOOKING_TOOLS = {
    "select_appointment_patient",
    "list_appointment_slots",
    "prepare_appointment",
    "book_appointment",
}


def execute_booking(db: Session, reg: Registration, name: str, args: dict) -> dict:
    from app.voice.tools import explicit_confirmation, validation_result

    service = AppointmentService(db)
    if reg.refusals.get("_booking_failures", 0) >= 3:
        return {
            "success": False,
            "error_type": "retry_limit_reached",
            "end_call": True,
            "next_action": "endCall",
            "message": "Booking attempts are closed. "
            "Any saved registration remains. Thank the caller and endCall.",
        }
    if name == "select_appointment_patient":
        if reg.patient_id:
            raise AppError(
                409,
                "patient_already_selected",
                "The saved patient is selected. "
                "Use list_appointment_slots; another patient needs a new call",
            )
        if reg.appointment_id:
            raise AppError(409, "already_booked", "One appointment per call; end this call")
        # A fresh selection attempt invalidates previous selection and consent,
        # even when the supplied identity does not match.
        reg.booking_patient_id = reg.appointment_slot = reg.appointment_token = None
        try:
            identity = BookingIdentity.model_validate(args)
            patient = PatientService(db).lookup(identity.phone_number)
            birth_date = identity.date_of_birth
        except (ValueError, TypeError):
            return {
                "success": False,
                "error_type": "validation_error",
                "message": "Ask for a valid registered phone number and date of birth.",
            }
        if not patient or patient.date_of_birth != birth_date:
            return {
                "success": False,
                "error_type": "not_found",
                "message": "No matching registration. Check the phone and birth date, "
                "or offer new-patient registration. Do not guess an identity.",
            }
        reg.booking_patient_id = patient.patient_id
        return {
            "success": True,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "next_action": "list_appointment_slots",
        }

    if name == "list_appointment_slots":
        slots = service.slots()
        days = sorted({slot.date().isoformat() for slot in slots})
        if args.get("date"):
            selected = TypeAdapter(date).validate_python(args["date"])
            slots = [slot for slot in slots if slot.date() == selected]
        return {
            "success": True,
            "description": SCHEDULE,
            "timezone": "UTC",
            "duration_minutes": 30,
            "available_dates": days,
            "slots": [slot.isoformat() for slot in slots[:6]],
            "message": "These are demonstration appointments, not real clinic visits. "
            "Offer these exact times in UTC; query a listed date for more options.",
        }

    patient_id = reg.patient_id or reg.booking_patient_id
    if not patient_id:
        raise AppError(
            400,
            "patient_required",
            "Save new registration first, or use "
            "select_appointment_patient with the returning caller's phone and DOB",
        )
    patient = PatientService(db).get(patient_id)
    if name == "prepare_appointment":
        if reg.appointment_id:
            raise AppError(409, "already_booked", "One appointment per call; end this call")
        # Return, rather than raise, to commit invalidation of an old token.
        reg.appointment_token = reg.appointment_slot = None
        try:
            slot = AppointmentSlot.model_validate(args).starts_at.astimezone(UTC)
        except ValidationError as exc:
            return validation_result(exc)
        if slot not in service.slots():
            return {
                "success": False,
                "error_type": "slot_unavailable",
                "next_action": "list_appointment_slots",
                "message": "That time is unavailable. Offer a fresh available time.",
            }
        reg.appointment_slot, reg.appointment_token = slot, str(uuid4())
        return {
            "success": True,
            "confirmation_token": reg.appointment_token,
            "readback": f"Shall I book a 30-minute demonstration appointment for "
            f"{patient.first_name} {patient.last_name} on "
            f"{slot.strftime('%A, %B %d, %Y at %H:%M')} UTC? "
            "This is not a visit with a real clinic.",
        }

    if (
        not reg.appointment_token
        or args.get("confirmation_token") != reg.appointment_token
        or not explicit_confirmation(args.get("caller_response"))
    ):
        counts = dict(reg.refusals)
        counts["_booking_failures"] = counts.get("_booking_failures", 0) + 1
        reg.refusals = counts
        exhausted = counts["_booking_failures"] >= 3
        if exhausted:
            reg.appointment_slot = reg.appointment_token = None
        return {
            "success": False,
            "error_type": "confirmation_required",
            "end_call": exhausted,
            "next_action": "endCall" if exhausted else "prepare_appointment",
            "message": "Booking was not confirmed. "
            + (
                "Stop retrying and end the call. Any previously saved registration remains."
                if exhausted
                else "Read back a freshly prepared slot and WAIT for clear consent."
            ),
        }
    if reg.appointment_id:
        existing = db.get(Appointment, reg.appointment_id)
        if existing and not existing.cancelled_at:
            return {
                "success": True,
                "already_booked": True,
                "appointment": AppointmentRead.model_validate(existing).model_dump(mode="json"),
            }
        raise AppError(409, "cancelled", "That booking was cancelled; start a new call to rebook")
    appointment = service.book(patient_id, reg.appointment_slot)
    reg.appointment_id = appointment.appointment_id
    return {
        "success": True,
        "appointment": AppointmentRead.model_validate(appointment).model_dump(mode="json"),
        "message": "The demonstration appointment is booked. Confirm the date and UTC time "
        "to the caller, then thank them and endCall. This is not a real clinic visit.",
    }
