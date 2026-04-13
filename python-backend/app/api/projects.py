from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db_session
from app.schemas import (
    ProjectCreate,
    ProjectDeleteResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdate,
)
from app.services import ProjectNotFoundError, ProjectService, ProjectStorageError

router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_project_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ProjectService:
    return ProjectService(session=session, settings=settings)


def _raise_project_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, ProjectNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ProjectStorageError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status_filter: ProjectStatus | None = Query(default=None, alias="status"),
    sort: str = Query(default="updated_at"),
    order: str = Query(default="desc"),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    projects, total = await project_service.list_projects(
        status=status_filter,
        sort=sort,
        order=order,
    )
    return ProjectListResponse(projects=projects, total=total)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    try:
        return await project_service.create_project(payload)
    except Exception as exc:
        _raise_project_http_error(exc)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project_detail(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectDetailResponse:
    try:
        return await project_service.get_project_detail(project_id)
    except Exception as exc:
        _raise_project_http_error(exc)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    try:
        return await project_service.update_project(project_id, payload)
    except Exception as exc:
        _raise_project_http_error(exc)


@router.delete("/{project_id}", response_model=ProjectDeleteResponse)
async def delete_project(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectDeleteResponse:
    try:
        await project_service.delete_project(project_id)
    except Exception as exc:
        _raise_project_http_error(exc)
    return ProjectDeleteResponse(success=True)
