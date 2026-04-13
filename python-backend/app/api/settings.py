from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db_session
from app.schemas import SettingsResponse, SettingsUpdate
from app.services import SettingsService, SettingsServiceError

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_settings_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> SettingsService:
    return SettingsService(session=session, settings=settings)


def _raise_settings_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, SettingsServiceError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=SettingsResponse)
async def get_app_settings(
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    try:
        return await settings_service.get_settings()
    except Exception as exc:
        _raise_settings_http_error(exc)


@router.put("", response_model=SettingsResponse)
async def update_app_settings(
    payload: SettingsUpdate,
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    try:
        return await settings_service.update_settings(payload)
    except Exception as exc:
        _raise_settings_http_error(exc)
