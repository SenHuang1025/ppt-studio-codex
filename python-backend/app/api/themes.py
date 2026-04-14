from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db_session
from app.schemas import ProjectDetailResponse, ThemeConfig, ThemeListResponse, ThemeSyncResponse
from app.services import (
    ProjectNotFoundError,
    ProjectService,
    ProjectStorageError,
    ThemeService,
    ThemeValidationError,
    ThemeWriteError,
)

router = APIRouter(tags=["themes"])


def get_project_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ProjectService:
    return ProjectService(session=session, settings=settings)


def get_theme_service(settings: Settings = Depends(get_settings)) -> ThemeService:
    return ThemeService(settings=settings)


def _raise_theme_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, ProjectNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ThemeValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, (ProjectStorageError, ThemeWriteError)):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    raise exc


@router.get("/api/themes", response_model=ThemeListResponse)
async def list_themes(theme_service: ThemeService = Depends(get_theme_service)) -> ThemeListResponse:
    return ThemeListResponse(themes=theme_service.list_presets())


@router.put("/api/projects/{project_id}/theme", response_model=ProjectDetailResponse)
async def update_project_theme(
    project_id: str,
    payload: ThemeConfig,
    project_service: ProjectService = Depends(get_project_service),
    theme_service: ThemeService = Depends(get_theme_service),
) -> ProjectDetailResponse:
    try:
        resolved_theme = theme_service.resolve_theme(payload)
        await project_service.save_theme_config(project_id, resolved_theme)
        theme_service.write_preview_theme(resolved_theme)
        return await project_service.get_project_detail(project_id)
    except Exception as exc:
        _raise_theme_http_error(exc)


@router.post("/api/projects/{project_id}/theme/sync", response_model=ThemeSyncResponse)
async def sync_project_theme(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
    theme_service: ThemeService = Depends(get_theme_service),
) -> ThemeSyncResponse:
    try:
        project = await project_service.get_project_detail(project_id)
        resolved_theme = theme_service.resolve_theme(project.theme_config)
        theme_service.write_preview_theme(resolved_theme)
        return ThemeSyncResponse(theme=resolved_theme)
    except Exception as exc:
        _raise_theme_http_error(exc)
