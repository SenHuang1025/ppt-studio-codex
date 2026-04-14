from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sse_starlette import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm import API_KEY_HEADER, LLMConfigurationError, MissingAPIKeyError, build_llm_runtime
from app.agents.page_generator import generate_page_code
from app.api.files import get_file_service
from app.api.projects import get_project_service
from app.api.settings import get_settings_service
from app.api.themes import get_theme_service
from app.config import Settings, get_settings
from app.db import get_db_session
from app.schemas import OutlineSchema
from app.services import (
    FileService,
    PageService,
    PageServiceError,
    PreviewSlideWriteError,
    ProjectNotFoundError,
    ProjectService,
    SSEManager,
    SettingsService,
    ThemeService,
)

router = APIRouter(prefix="/api/projects/{project_id}/pages", tags=["pages"])


def get_page_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> PageService:
    return PageService(session=session, settings=settings)


def get_sse_manager(request: Request) -> SSEManager:
    sse_manager = getattr(request.app.state, "sse_manager", None)
    if not isinstance(sse_manager, SSEManager):
        raise RuntimeError("SSE manager is not initialized on the FastAPI application.")
    return sse_manager


def _raise_page_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (MissingAPIKeyError, LLMConfigurationError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.post("/{page_number}/generate")
async def generate_single_page(
    project_id: str,
    page_number: int,
    request: Request,
    file_service: FileService = Depends(get_file_service),
    page_service: PageService = Depends(get_page_service),
    project_service: ProjectService = Depends(get_project_service),
    settings_service: SettingsService = Depends(get_settings_service),
    sse_manager: SSEManager = Depends(get_sse_manager),
    theme_service: ThemeService = Depends(get_theme_service),
) -> EventSourceResponse:
    api_key = request.headers.get(API_KEY_HEADER, "").strip()

    try:
        llm_runtime = await build_llm_runtime(
            settings_service=settings_service,
            api_key=api_key,
        )
    except Exception as exc:
        _raise_page_http_error(exc)

    stream_id, stream = await sse_manager.open_stream(project_id)

    async def stream_response() -> AsyncGenerator[object, None]:
        producer_task = asyncio.create_task(
            _produce_page_generation_events(
                file_service=file_service,
                llm_runtime=llm_runtime,
                page_number=page_number,
                page_service=page_service,
                project_id=project_id,
                project_service=project_service,
                sse_manager=sse_manager,
                stream_id=stream_id,
                theme_service=theme_service,
            )
        )

        try:
            async for event in stream:
                if await request.is_disconnected():
                    producer_task.cancel()
                    break

                yield event
        finally:
            if not producer_task.done():
                producer_task.cancel()

            try:
                await producer_task
            except asyncio.CancelledError:
                pass

            await sse_manager.close_stream(project_id, stream_id=stream_id)

    return EventSourceResponse(stream_response(), ping=None)


async def _produce_page_generation_events(
    *,
    file_service: FileService,
    llm_runtime: Any,
    page_number: int,
    page_service: PageService,
    project_id: str,
    project_service: ProjectService,
    sse_manager: SSEManager,
    stream_id: str,
    theme_service: ThemeService,
) -> None:
    cancelled = False

    async def sse_callback(event: str, data: dict[str, object]) -> None:
        await sse_manager.send_event(project_id, event, data, stream_id=stream_id)

    try:
        project = await project_service.get_project_detail(project_id)
        if project.outline is None:
            await _safe_send_event(
                sse_manager,
                project_id,
                "error",
                {"message": "当前项目还没有可用大纲，请先完成大纲规划。"},
                stream_id=stream_id,
            )
            return

        outline = OutlineSchema.model_validate(project.outline)
        if page_number < 1 or page_number > len(outline.pages):
            await _safe_send_event(
                sse_manager,
                project_id,
                "error",
                {
                    "message": (
                        f"页码 {page_number} 超出当前大纲范围。"
                        f"当前有效范围为 1 到 {len(outline.pages)}。"
                    )
                },
                stream_id=stream_id,
            )
            return

        outline_page = outline.pages[page_number - 1]
        parsed_contents = await _load_page_generation_sources(
            file_service=file_service,
            project_id=project_id,
        )
        resolved_theme = theme_service.resolve_theme(project.theme_config)
        theme_service.write_preview_theme(resolved_theme)

        page_generation_context = page_service.build_page_generation_context(
            project=project,
            outline_page=outline_page,
            parsed_contents=parsed_contents,
        )
        page_code = await generate_page_code(
            project=project,
            outline_page=outline_page,
            parsed_contents=parsed_contents,
            theme_config=resolved_theme,
            current_page_number=page_number,
            total_pages=outline.total_pages,
            existing_page_code=_resolve_existing_page_code(project=project, page_number=page_number),
            model=llm_runtime.chat_model,
            deliberation_enabled=llm_runtime.settings.multi_agent_deliberation_enabled,
            sse_callback=sse_callback,
            page_generation_context=page_generation_context,
        )

        page_service.write_preview_slide(page_number=page_number, vue_code=page_code)
        await page_service.upsert_generated_page(
            project_id=project_id,
            page_number=page_number,
            title=outline_page.title,
            page_type=outline_page.type,
            vue_code=page_code,
        )

        await _safe_send_event(
            sse_manager,
            project_id,
            "page_complete",
            {
                "page_number": page_number,
                "title": outline_page.title,
                "status": "generated",
                "vue_code": page_code,
            },
            stream_id=stream_id,
        )
    except asyncio.CancelledError:
        cancelled = True
        logger.info("Page generation stream was cancelled for project {}", project_id)
        raise
    except ProjectNotFoundError as exc:
        await _safe_send_event(
            sse_manager,
            project_id,
            "error",
            {"message": str(exc)},
            stream_id=stream_id,
        )
    except (PageServiceError, PreviewSlideWriteError) as exc:
        await _safe_send_event(
            sse_manager,
            project_id,
            "error",
            {"message": str(exc)},
            stream_id=stream_id,
        )
    except Exception as exc:
        logger.exception("Single-page generation SSE flow failed for project {}", project_id)
        await _safe_send_event(
            sse_manager,
            project_id,
            "error",
            {
                "message": f"单页生成失败：{str(exc) or exc.__class__.__name__}",
            },
            stream_id=stream_id,
        )
    finally:
        if cancelled:
            await sse_manager.close_stream(project_id, stream_id=stream_id)
            return

        await _safe_send_event(
            sse_manager,
            project_id,
            "done",
            {},
            stream_id=stream_id,
        )


async def _load_page_generation_sources(
    *,
    file_service: FileService,
    project_id: str,
) -> list[dict[str, Any]]:
    uploaded_files = await file_service.list_files(project_id)
    sources: list[dict[str, Any]] = []

    for uploaded_file in uploaded_files:
        parsed_content = uploaded_file.parsed_content or {}
        sources.append(
            {
                "file_id": uploaded_file.id,
                "file_name": uploaded_file.original_name,
                "file_type": uploaded_file.file_type,
                "summary": _normalized_text(parsed_content.get("summary")),
                "key_points": _normalized_string_list(parsed_content.get("key_points")),
                "structured_data": parsed_content.get("structured_data")
                if isinstance(parsed_content.get("structured_data"), dict)
                else {},
                "text_content": _normalized_text(parsed_content.get("text_content")),
            }
        )

    return sources


def _resolve_existing_page_code(*, project: Any, page_number: int) -> str | None:
    pages = getattr(project, "pages", None) or []
    for page in pages:
        if getattr(page, "page_number", None) == page_number:
            return getattr(page, "vue_code", None)
    return None


def _normalized_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _normalized_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value:
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                normalized.append(stripped)
    return normalized


async def _safe_send_event(
    sse_manager: SSEManager,
    project_id: str,
    event: str,
    data: dict[str, object],
    *,
    stream_id: str,
) -> None:
    try:
        await sse_manager.send_event(project_id, event, data, stream_id=stream_id)
    except Exception:
        logger.exception("Failed to send SSE event {} for project {}", event, project_id)
