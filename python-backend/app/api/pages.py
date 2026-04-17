from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from loguru import logger
from sse_starlette import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm import API_KEY_HEADER, InvalidAPIKeyError, LLMConfigurationError, MissingAPIKeyError, build_llm_runtime
from app.agents.page_generator import generate_page_code
from app.api.files import get_file_service
from app.api.projects import get_project_service
from app.api.settings import get_settings_service
from app.api.themes import get_theme_service
from app.config import Settings, get_settings
from app.db import get_db_session
from app.schemas import (
    OutlinePageSchema,
    OutlineSchema,
    PageInsertAfterRequest,
    PageMutationResponse,
    PageReorderRequest,
    PageResponse,
    PageRollbackRequest,
    PageVersionResponse,
)
from app.services import (
    FileService,
    InvalidPageOrderError,
    PageMutationValidationError,
    PageNotFoundError,
    PageService,
    PageServiceError,
    PageStorageError,
    PageVersionNotFoundError,
    PreviewSlideWriteError,
    ProjectNotFoundError,
    ProjectService,
    SSEManager,
    SettingsService,
    ThemeService,
    ThumbnailDependencyError,
    ThumbnailNotFoundError,
    ThumbnailRenderError,
    ThumbnailService,
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


def get_thumbnail_service(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ThumbnailService:
    thumbnail_service = getattr(request.app.state, "thumbnail_service", None)
    if not isinstance(thumbnail_service, ThumbnailService):
        thumbnail_service = ThumbnailService(settings=settings)
        request.app.state.thumbnail_service = thumbnail_service
    return thumbnail_service


def _raise_page_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, PageNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, PageVersionNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, (InvalidPageOrderError, PageMutationValidationError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, (PageStorageError, PageServiceError, PreviewSlideWriteError)):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    if isinstance(exc, ThumbnailNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, (ThumbnailDependencyError, ThumbnailRenderError)):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    if isinstance(exc, (MissingAPIKeyError, InvalidAPIKeyError, LLMConfigurationError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/{page_number}/thumbnail")
async def get_page_thumbnail(
    project_id: str,
    page_number: int,
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
) -> FileResponse:
    try:
        thumbnail_path = thumbnail_service.require_thumbnail_path(
            project_id=project_id,
            page_number=page_number,
        )
        return FileResponse(
            path=thumbnail_path,
            media_type="image/png",
            filename=thumbnail_path.name,
        )
    except Exception as exc:
        _raise_page_http_error(exc)


@router.post("/{page_number}/confirm", response_model=PageResponse)
async def confirm_page(
    project_id: str,
    page_number: int,
    page_service: PageService = Depends(get_page_service),
) -> PageResponse:
    try:
        return await page_service.confirm_page(
            project_id=project_id,
            page_number=page_number,
        )
    except Exception as exc:
        _raise_page_http_error(exc)


@router.get("/{page_number}/versions", response_model=list[PageVersionResponse])
async def list_page_versions(
    project_id: str,
    page_number: int,
    page_service: PageService = Depends(get_page_service),
) -> list[PageVersionResponse]:
    try:
        return await page_service.list_page_versions(
            project_id=project_id,
            page_number=page_number,
        )
    except Exception as exc:
        _raise_page_http_error(exc)


@router.post("/{page_number}/rollback", response_model=PageResponse)
async def rollback_page(
    project_id: str,
    page_number: int,
    payload: PageRollbackRequest,
    page_service: PageService = Depends(get_page_service),
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
) -> PageResponse:
    try:
        page = await page_service.rollback_page_to_version(
            project_id=project_id,
            page_number=page_number,
            target_version=payload.version,
        )
        page_service.write_preview_slide(page_number=page_number, vue_code=str(page.vue_code or ""))
        await _safe_refresh_page_thumbnail(
            project_id=project_id,
            page_numbers=[page_number],
            thumbnail_service=thumbnail_service,
        )
        return page
    except Exception as exc:
        _raise_page_http_error(exc)


@router.post("/{page_number}/versions/{version}/preview", response_model=PageVersionResponse)
async def preview_page_version(
    project_id: str,
    page_number: int,
    version: int,
    page_service: PageService = Depends(get_page_service),
) -> PageVersionResponse:
    try:
        versions = await page_service.list_page_versions(
            project_id=project_id,
            page_number=page_number,
        )
        target = next((item for item in versions if item.version == version), None)
        if target is None:
            raise PageVersionNotFoundError(project_id, page_number, version)
        page_service.write_version_preview_slide(
            page_number=page_number,
            vue_code=target.vue_code,
        )
        return target
    except Exception as exc:
        _raise_page_http_error(exc)


@router.delete("/{page_number}", response_model=PageMutationResponse)
async def delete_page(
    project_id: str,
    page_number: int,
    page_service: PageService = Depends(get_page_service),
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
) -> PageMutationResponse:
    try:
        await page_service.delete_page(project_id=project_id, page_number=page_number)
        await _safe_refresh_project_thumbnails(
            project_id=project_id,
            page_service=page_service,
            thumbnail_service=thumbnail_service,
        )
        return PageMutationResponse()
    except Exception as exc:
        _raise_page_http_error(exc)


@router.post("/{page_number}/duplicate", response_model=PageResponse)
async def duplicate_page(
    project_id: str,
    page_number: int,
    page_service: PageService = Depends(get_page_service),
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
) -> PageResponse:
    try:
        page = await page_service.duplicate_page(project_id=project_id, page_number=page_number)
        await _safe_refresh_project_thumbnails(
            project_id=project_id,
            page_service=page_service,
            thumbnail_service=thumbnail_service,
        )
        return page
    except Exception as exc:
        _raise_page_http_error(exc)


@router.put("/reorder", response_model=PageMutationResponse)
async def reorder_pages(
    project_id: str,
    payload: PageReorderRequest,
    page_service: PageService = Depends(get_page_service),
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
) -> PageMutationResponse:
    try:
        await page_service.reorder_pages(
            project_id=project_id,
            ordered_page_numbers=payload.page_numbers,
        )
        await _safe_refresh_project_thumbnails(
            project_id=project_id,
            page_service=page_service,
            thumbnail_service=thumbnail_service,
        )
        return PageMutationResponse()
    except Exception as exc:
        _raise_page_http_error(exc)


@router.post("/{page_number}/insert-after", response_model=PageResponse)
async def insert_page_after(
    project_id: str,
    page_number: int,
    payload: PageInsertAfterRequest,
    request: Request,
    file_service: FileService = Depends(get_file_service),
    page_service: PageService = Depends(get_page_service),
    project_service: ProjectService = Depends(get_project_service),
    settings_service: SettingsService = Depends(get_settings_service),
    theme_service: ThemeService = Depends(get_theme_service),
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
) -> PageResponse:
    api_key = request.headers.get(API_KEY_HEADER, "").strip()

    try:
        llm_runtime = await build_llm_runtime(
            settings_service=settings_service,
            api_key=api_key,
        )
        project = await project_service.get_project_detail(project_id)
        total_pages_before_insert = _resolve_insert_total_pages(project)
        if page_number < 1 or page_number > total_pages_before_insert:
            raise PageNotFoundError(project_id, page_number)

        outline = _resolve_outline_for_insert(project=project, after_page_number=page_number, description=payload.description)
        parsed_contents = await _load_page_generation_sources(file_service=file_service, project_id=project_id)
        resolved_theme = theme_service.resolve_theme(project.theme_config)
        theme_service.write_preview_theme(resolved_theme)
        page_generation_context = page_service.build_page_generation_context(
            project=project,
            outline_page=outline,
            parsed_contents=parsed_contents,
        )
        total_pages_after_insert = total_pages_before_insert + 1
        page_code = await generate_page_code(
            project=project,
            outline_page=outline,
            parsed_contents=parsed_contents,
            theme_config=resolved_theme,
            current_page_number=outline.page_number,
            total_pages=total_pages_after_insert,
            existing_page_code=None,
            model=llm_runtime.chat_model,
            deliberation_enabled=llm_runtime.settings.multi_agent_deliberation_enabled,
            page_generation_context=page_generation_context,
        )
        page = await page_service.insert_generated_page_after(
            project_id=project_id,
            after_page_number=page_number,
            outline_page=outline,
            vue_code=page_code,
            change_description=f"插入新页：{_truncate_insert_description(payload.description)}",
        )
        await _safe_refresh_project_thumbnails(
            project_id=project_id,
            page_service=page_service,
            thumbnail_service=thumbnail_service,
        )
        return page
    except Exception as exc:
        _raise_page_http_error(exc)


@router.post("/{page_number}/generate")
@router.post("/{page_number}/regenerate")
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
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
) -> EventSourceResponse:
    api_key = request.headers.get(API_KEY_HEADER, "").strip()
    requested_stream_id = request.headers.get("x-ppt-studio-stream-id", "").strip() or None

    try:
        llm_runtime = await build_llm_runtime(
            settings_service=settings_service,
            api_key=api_key,
        )
    except Exception as exc:
        _raise_page_http_error(exc)

    if requested_stream_id and await sse_manager.has_stream(project_id, stream_id=requested_stream_id):
        stream_id = requested_stream_id
        stream = await sse_manager.create_stream(project_id, stream_id=stream_id)
    else:
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
                thumbnail_service=thumbnail_service,
            )
        )
        await sse_manager.register_producer_task(project_id, stream_id=stream_id, producer_task=producer_task)

        try:
            async for event in stream:
                if await request.is_disconnected():
                    await sse_manager.mark_client_disconnected(project_id, stream_id=stream_id)
                    break

                yield event
        finally:
            if not producer_task.done():
                producer_task.cancel()

            try:
                await producer_task
            except asyncio.CancelledError:
                pass

            if producer_task.done():
                await sse_manager.close_stream(project_id, stream_id=stream_id)

    return EventSourceResponse(stream_response(), ping=None, headers={"x-ppt-studio-stream-id": stream_id})


@router.post("/streams/{stream_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_page_stream(
    project_id: str,
    stream_id: str,
    sse_manager: SSEManager = Depends(get_sse_manager),
) -> None:
    await sse_manager.cancel_stream(project_id, stream_id=stream_id)


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
    thumbnail_service: ThumbnailService,
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
        saved_page = await page_service.upsert_generated_page(
            project_id=project_id,
            page_number=page_number,
            title=outline_page.title,
            page_type=outline_page.type,
            vue_code=page_code,
        )
        await _safe_refresh_page_thumbnail(
            project_id=project_id,
            page_numbers=[page_number],
            thumbnail_service=thumbnail_service,
        )

        await _safe_send_event(
            sse_manager,
            project_id,
            "page_complete",
            {
                "page_number": page_number,
                "title": outline_page.title,
                "status": "generated",
                "version": getattr(saved_page, "version", None),
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


def _resolve_outline_for_insert(*, project: Any, after_page_number: int, description: str) -> OutlinePageSchema:
    next_page_number = after_page_number + 1
    normalized_description = description.strip()
    title = _derive_insert_page_title(normalized_description, next_page_number)
    reference_layout = _resolve_reference_outline_layout(project=project, after_page_number=after_page_number)

    return OutlinePageSchema(
        page_number=next_page_number,
        title=title,
        type="content",
        content_brief=normalized_description,
        layout=reference_layout,
        data_refs=[],
    )


def _resolve_reference_outline_layout(*, project: Any, after_page_number: int) -> str:
    outline = getattr(project, "outline", None)
    pages = outline.get("pages") if isinstance(outline, dict) else None
    if isinstance(pages, list):
        for page in pages:
            if isinstance(page, dict) and page.get("page_number") == after_page_number:
                layout = _normalized_text(page.get("layout"))
                if layout:
                    return layout

    return "title-body"


def _resolve_insert_total_pages(project: Any) -> int:
    outline = getattr(project, "outline", None)
    outline_total = outline.get("total_pages") if isinstance(outline, dict) else 0
    pages = getattr(project, "pages", None) or []
    highest_page_number = max(
        (getattr(page, "page_number", 0) or 0 for page in pages),
        default=0,
    )
    return max(int(getattr(project, "total_pages", 0) or 0), int(outline_total or 0), int(highest_page_number or 0))


def _derive_insert_page_title(description: str, page_number: int) -> str:
    normalized = " ".join(description.split())
    if not normalized:
        return f"新增第 {page_number} 页"

    first_sentence = normalized
    for separator in ("。", "！", "？", "\n"):
        if separator in first_sentence:
            first_sentence = first_sentence.split(separator, 1)[0].strip()
            break

    if len(first_sentence) <= 28:
        return first_sentence
    return f"{first_sentence[:25].rstrip()}..."


def _truncate_insert_description(description: str) -> str:
    normalized = " ".join(description.split())
    if len(normalized) <= 40:
        return normalized
    return f"{normalized[:37].rstrip()}..."


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


async def _safe_refresh_page_thumbnail(
    *,
    project_id: str,
    page_numbers: list[int],
    thumbnail_service: ThumbnailService,
) -> None:
    try:
        await thumbnail_service.refresh_from_preview(
            project_id=project_id,
            page_numbers=page_numbers,
        )
    except Exception:
        logger.exception("Failed to refresh thumbnail for project {} pages {}", project_id, page_numbers)


async def _safe_refresh_project_thumbnails(
    *,
    project_id: str,
    page_service: PageService,
    thumbnail_service: ThumbnailService,
) -> None:
    try:
        await page_service.refresh_project_thumbnails(
            project_id=project_id,
            thumbnail_service=thumbnail_service,
        )
    except Exception:
        logger.exception("Failed to refresh project thumbnails for project {}", project_id)
