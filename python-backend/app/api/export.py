from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db_session
from app.schemas import ProjectExportTaskResponse
from app.services import (
    ExportArtifactNotReadyError,
    ExportConflictError,
    ExportDependencyError,
    ExportPageSnapshot,
    ExportProjectSnapshot,
    ExportRenderError,
    ExportTaskManager,
    ExportTaskNotFoundError,
    ExportValidationError,
    ProjectNotFoundError,
    ProjectService,
    ThemeService,
)

router = APIRouter(tags=["exports"])


def get_project_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ProjectService:
    return ProjectService(session=session, settings=settings)


def get_theme_service(settings: Settings = Depends(get_settings)) -> ThemeService:
    return ThemeService(settings=settings)


def get_export_task_manager(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ExportTaskManager:
    manager = getattr(request.app.state, "export_task_manager", None)
    if not isinstance(manager, ExportTaskManager):
        manager = ExportTaskManager(settings=settings)
        request.app.state.export_task_manager = manager
    return manager


def _raise_export_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, ProjectNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ExportTaskNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ExportArtifactNotReadyError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ExportConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ExportValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, (ExportDependencyError, ExportRenderError)):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    raise exc


@router.post(
    "/api/projects/{project_id}/export/pdf",
    response_model=ProjectExportTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_pdf_export(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
    theme_service: ThemeService = Depends(get_theme_service),
    export_task_manager: ExportTaskManager = Depends(get_export_task_manager),
) -> ProjectExportTaskResponse:
    try:
        project = await project_service.get_project_detail(project_id)
        snapshot = _build_export_snapshot(project=project, theme_service=theme_service)
        task = await export_task_manager.start_pdf_export(snapshot)
        return _serialize_task(project_id=project_id, task=task)
    except Exception as exc:
        _raise_export_http_error(exc)


@router.get("/api/projects/{project_id}/export/tasks/{task_id}", response_model=ProjectExportTaskResponse)
async def get_export_task(
    project_id: str,
    task_id: str,
    export_task_manager: ExportTaskManager = Depends(get_export_task_manager),
) -> ProjectExportTaskResponse:
    try:
        task = export_task_manager.get_task(project_id=project_id, task_id=task_id)
        return _serialize_task(project_id=project_id, task=task)
    except Exception as exc:
        _raise_export_http_error(exc)


@router.get("/api/projects/{project_id}/export/tasks/{task_id}/download")
async def download_export_artifact(
    project_id: str,
    task_id: str,
    export_task_manager: ExportTaskManager = Depends(get_export_task_manager),
) -> FileResponse:
    try:
        task, artifact_path = export_task_manager.require_artifact(project_id=project_id, task_id=task_id)
        return FileResponse(
            path=artifact_path,
            media_type="application/pdf",
            filename=task.artifact_name or artifact_path.name,
        )
    except Exception as exc:
        _raise_export_http_error(exc)


def _build_export_snapshot(*, project: object, theme_service: ThemeService) -> ExportProjectSnapshot:
    outline = getattr(project, "outline", None)
    outline_total_pages = 0
    if isinstance(outline, dict):
        outline_total_pages = int(outline.get("total_pages", 0) or 0)
    elif outline is not None:
        outline_total_pages = int(getattr(outline, "total_pages", 0) or 0)
    expected_total_pages = max(int(getattr(project, "total_pages", 0) or 0), int(outline_total_pages or 0))

    export_pages = [
        page
        for page in sorted(getattr(project, "pages", []) or [], key=lambda item: int(item.page_number))
        if str(getattr(page, "vue_code", "") or "").strip()
    ]

    if not export_pages:
        raise ExportValidationError("当前项目还没有生成可导出的页面。")

    exported_page_numbers = [int(page.page_number) for page in export_pages]
    expected_page_numbers = list(range(1, expected_total_pages + 1))
    if expected_total_pages > 0 and exported_page_numbers != expected_page_numbers:
        raise ExportValidationError("当前还有页面未生成完成，请等待全部页面可预览后再导出 PDF。")

    return ExportProjectSnapshot(
        project_id=str(getattr(project, "id")),
        project_name=str(getattr(project, "name") or "ppt-studio-export"),
        total_pages=len(export_pages),
        theme=theme_service.resolve_theme(getattr(project, "theme_config", None)),
        pages=tuple(
            ExportPageSnapshot(
                page_number=int(getattr(page, "page_number")),
                title=str(getattr(page, "title", None) or f"第 {int(getattr(page, 'page_number'))} 页"),
                vue_code=str(getattr(page, "vue_code", "") or ""),
            )
            for page in export_pages
        ),
    )


def _serialize_task(*, project_id: str, task: object) -> ProjectExportTaskResponse:
    download_url = (
        f"/api/projects/{project_id}/export/tasks/{getattr(task, 'id')}/download"
        if getattr(task, "artifact_path", None) is not None
        else None
    )

    return ProjectExportTaskResponse.model_validate(
        {
            "id": getattr(task, "id"),
            "project_id": getattr(task, "project_id"),
            "format": getattr(task, "export_format"),
            "status": getattr(task, "status"),
            "stage": getattr(task, "stage"),
            "total_pages": getattr(task, "total_pages"),
            "completed_pages": getattr(task, "completed_pages"),
            "current_page_number": getattr(task, "current_page_number"),
            "current_page_title": getattr(task, "current_page_title"),
            "progress": getattr(task, "progress"),
            "error": getattr(task, "error"),
            "artifact_name": getattr(task, "artifact_name"),
            "artifact_size_bytes": getattr(task, "artifact_size_bytes"),
            "download_url": download_url,
            "created_at": getattr(task, "created_at"),
            "updated_at": getattr(task, "updated_at"),
        }
    )
