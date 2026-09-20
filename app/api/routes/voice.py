import secrets

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.db.session import get_db
from app.voice.vapi import Webhook, process

router = APIRouter(prefix="/voice", tags=["Voice"])


def verify_webhook(x_vapi_secret: str | None = Header(None)):
    if not settings.vapi_webhook_secret:
        raise AppError(503, "not_configured", "Vapi webhook secret is not configured")
    if not secrets.compare_digest(x_vapi_secret or "", settings.vapi_webhook_secret):
        raise AppError(401, "unauthorized", "Invalid webhook credentials")


@router.post("/vapi", dependencies=[Depends(verify_webhook)])
def webhook(payload: Webhook, db: Session = Depends(get_db)):
    """Authenticated Vapi server webhook. Tool results follow Vapi's results protocol."""
    return process(db, payload.message)
