import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException

from app.api.routes import health, patients, voice
from app.core.config import settings
from app.core.exceptions import AppError, error_body
from app.core.logging import event

logging.basicConfig(level=settings.log_level, format="%(message)s")
app = FastAPI(
    title="Voice AI Agent — Patient Registration System",
    version="1.0.0",
    description="Assessment demo. DO NOT ENTER REAL PATIENT DATA.",
)
app.include_router(health.router)
app.include_router(patients.router)
app.include_router(voice.router)


@app.exception_handler(AppError)
async def application_error(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status, content=error_body(exc.code, exc.message, exc.details)
    )


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_error(request: Request, exc):
    details = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content=error_body("validation_error", "Please correct the specified fields", details),
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code, content=error_body("http_error", str(exc.detail))
    )


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc):
    return JSONResponse(
        status_code=409, content=error_body("conflict", "A conflicting record already exists")
    )


@app.exception_handler(SQLAlchemyError)
@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    event("write_failure", path=request.url.path, error_type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content=error_body(
            "system_error", "The operation could not be completed; please try again shortly"
        ),
    )
