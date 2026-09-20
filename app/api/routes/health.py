from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.patient import Envelope

router = APIRouter()


@router.get("/health", response_model=Envelope[dict], tags=["Health"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"data": {"status": "ok"}, "error": None}
