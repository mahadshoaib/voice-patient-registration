import secrets

from fastapi import Depends
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.core.exceptions import AppError

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str | None = Depends(api_key_header)):
    if settings.api_key and not secrets.compare_digest(key or "", settings.api_key):
        raise AppError(401, "unauthorized", "Valid X-API-Key required")
