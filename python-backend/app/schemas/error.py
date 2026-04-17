from __future__ import annotations

from app.schemas.base import APIModel


class ErrorResponse(APIModel):
    error: str
    detail: str | None = None
