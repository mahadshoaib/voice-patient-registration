from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard", include_in_schema=False)
def dashboard():
    # The shell is public; every data request requires the existing reviewer key.
    return FileResponse(
        Path(__file__).resolve().parents[2] / "static" / "dashboard.html",
        headers={"Cache-Control": "no-store"},
    )
