from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sse_starlette import EventSourceResponse

from app.agents import API_KEY_HEADER, AgentGraphContext, build_llm_runtime, run_agent_workflow
from app.agents.page_generator import generate_page_code
from app.agents.llm import InvalidAPIKeyError, LLMConfigurationError, MissingAPIKeyError
from app.api.chat import get_chat_service
from app.api.files import get_file_service
from app.api.pages import get_page_service, get_thumbnail_service
from app.api.projects import get_project_service
from app.api.settings import get_settings_service
from app.api.themes import get_theme_service
from app.schemas import (
    AgentChatRequest,
    AgentConfirmOutlineRequest,
    OutlineSchema,
    ProjectStatus,
    ProjectUpdate,
)
from app.services import (
    ChatService,
    FileService,
    PageService,
    ProjectNotFoundError,
    ProjectService,
    SSEManager,
    SettingsService,
    ThemeService,
    ThumbnailService,
)

router = APIRouter(prefix="/api/projects/{project_id}/agent", tags=["agent"])


def get_sse_manager(request: Request) -> SSEManager:
    sse_manager = getattr(request.app.state, "sse_manager", None)
    if not isinstance(sse_manager, SSEManager):
        raise RuntimeError("SSE manager is not initialized on the FastAPI application.")
    return sse_manager


def _raise_agent_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (MissingAPIKeyError, InvalidAPIKeyError, LLMConfigurationError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.post("/chat")
async def chat_with_agent(
    project_id: str,
    payload: AgentChatRequest,
    request: Request,
    file_service: FileService = Depends(get_file_service),
    chat_service: ChatService = Depends(get_chat_service),
    page_service: PageService = Depends(get_page_service),
    project_service: ProjectService = Depends(get_project_service),
    settings_service: SettingsService = Depends(get_settings_service),
    sse_manager: SSEManager = Depends(get_sse_manager),
    theme_service: ThemeService = Depends(get_theme_service),
) -> EventSourceResponse:
    api_key = request.headers.get(API_KEY_HEADER, "").strip()
    requested_stream_id = request.headers.get("x-ppt-studio-stream-id", "").strip() or None

    try:
        llm_runtime = await build_llm_runtime(
            settings_service=settings_service,
            api_key=api_key,
        )
    except Exception as exc:
        _raise_agent_http_error(exc)

    if requested_stream_id and await sse_manager.has_stream(project_id, stream_id=requested_stream_id):
        stream_id = requested_stream_id
        stream = await sse_manager.create_stream(project_id, stream_id=stream_id)
    else:
        stream_id, stream = await sse_manager.open_stream(project_id)

    async def stream_response() -> AsyncGenerator[object, None]:
        producer_task = asyncio.create_task(
            _produce_agent_events(
                file_service=file_service,
                chat_service=chat_service,
                page_service=page_service,
                project_id=project_id,
                project_service=project_service,
                request_payload=payload,
                sse_manager=sse_manager,
                stream_id=stream_id,
                theme_service=theme_service,
                llm_runtime=llm_runtime,
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


@router.post("/confirm-outline")
async def confirm_outline(
    project_id: str,
    payload: AgentConfirmOutlineRequest,
    request: Request,
    chat_service: ChatService = Depends(get_chat_service),
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
        _raise_agent_http_error(exc)

    if requested_stream_id and await sse_manager.has_stream(project_id, stream_id=requested_stream_id):
        stream_id = requested_stream_id
        stream = await sse_manager.create_stream(project_id, stream_id=stream_id)
    else:
        stream_id, stream = await sse_manager.open_stream(project_id)

    async def stream_response() -> AsyncGenerator[object, None]:
        producer_task = asyncio.create_task(
            _produce_confirm_outline_events(
                chat_service=chat_service,
                file_service=file_service,
                llm_runtime=llm_runtime,
                page_service=page_service,
                project_id=project_id,
                project_service=project_service,
                request_payload=payload,
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
async def cancel_agent_stream(
    project_id: str,
    stream_id: str,
    sse_manager: SSEManager = Depends(get_sse_manager),
) -> None:
    await sse_manager.cancel_stream(project_id, stream_id=stream_id)


async def _produce_agent_events(
    *,
    chat_service: ChatService,
    file_service: FileService,
    page_service: PageService,
    project_id: str,
    project_service: ProjectService,
    request_payload: AgentChatRequest,
    sse_manager: SSEManager,
    stream_id: str,
    theme_service: ThemeService,
    llm_runtime: object,
) -> None:
    cancelled = False

    async def sse_callback(event: str, data: dict[str, object]) -> None:
        await sse_manager.send_event(project_id, event, data, stream_id=stream_id)

    try:
        user_message = await chat_service.create_message(
            project_id=project_id,
            role="user",
            content=request_payload.message,
            message_type="text",
            page_number=request_payload.page_number,
        )
        final_state = await run_agent_workflow(
            project_id=project_id,
            message=request_payload.message,
            page_number=request_payload.page_number,
            context=AgentGraphContext(
                chat_service=chat_service,
                file_service=file_service,
                page_service=page_service,
                project_service=project_service,
                theme_service=theme_service,
                llm_runtime=llm_runtime,
            ),
            sse_callback=sse_callback,
            exclude_history_message_id=user_message.id,
        )
        await _persist_assistant_message(
            chat_service=chat_service,
            project_id=project_id,
            final_state=final_state,
        )
    except asyncio.CancelledError:
        cancelled = True
        logger.info("Agent chat stream was cancelled for project {}", project_id)
        raise
    except ProjectNotFoundError as exc:
        await _safe_send_event(
            sse_manager,
            project_id,
            "error",
            {"message": str(exc)},
            stream_id=stream_id,
        )
    except Exception as exc:
        logger.exception("Agent chat SSE flow failed for project {}", project_id)
        await _safe_send_event(
            sse_manager,
            project_id,
            "error",
            {
                "message": f"实时会话失败：{str(exc) or exc.__class__.__name__}",
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


async def _produce_confirm_outline_events(
    *,
    chat_service: ChatService,
    file_service: FileService,
    llm_runtime: object,
    page_service: PageService,
    project_id: str,
    project_service: ProjectService,
    request_payload: AgentConfirmOutlineRequest,
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
        resolved_outline = request_payload.outline or project.outline

        if resolved_outline is None:
            await _safe_send_event(
                sse_manager,
                project_id,
                "error",
                {"message": "当前项目还没有可确认的大纲，请先在对话模式里生成或调整大纲。"},
                stream_id=stream_id,
            )
            return

        outline_schema = (
            resolved_outline if isinstance(resolved_outline, OutlineSchema) else OutlineSchema.model_validate(resolved_outline)
        )
        project = await project_service.save_outline(project_id, outline_schema)
        project = await project_service.update_project(
            project_id,
            ProjectUpdate(status=ProjectStatus.GENERATING),
        )
        project = await project_service.get_project_detail(project_id)

        assistant_message = _build_confirm_outline_message(outline_schema)
        await chat_service.create_message(
            project_id=project_id,
            role="assistant",
            content=assistant_message,
            message_type="text",
        )
        await _safe_send_event(
            sse_manager,
            project_id,
            "assistant_message",
            {"content": assistant_message},
            stream_id=stream_id,
        )

        parsed_contents = await _load_page_generation_sources(
            file_service=file_service,
            project_id=project_id,
        )
        resolved_theme = theme_service.resolve_theme(project.theme_config)
        theme_service.write_preview_theme(resolved_theme)
        existing_page_code_map = {
            page.page_number: getattr(page, "vue_code", None)
            for page in getattr(project, "pages", []) or []
        }

        for outline_page in outline_schema.pages:
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
                current_page_number=outline_page.page_number,
                total_pages=outline_schema.total_pages,
                existing_page_code=existing_page_code_map.get(outline_page.page_number),
                model=llm_runtime.chat_model,
                deliberation_enabled=llm_runtime.settings.multi_agent_deliberation_enabled,
                sse_callback=sse_callback,
                page_generation_context=page_generation_context,
            )

            page_service.write_preview_slide(
                page_number=outline_page.page_number,
                vue_code=page_code,
            )
            saved_page = await page_service.upsert_generated_page(
                project_id=project_id,
                page_number=outline_page.page_number,
                title=outline_page.title,
                page_type=outline_page.type,
                vue_code=page_code,
            )
            existing_page_code_map[outline_page.page_number] = page_code
            try:
                await thumbnail_service.refresh_from_preview(
                    project_id=project_id,
                    page_numbers=[outline_page.page_number],
                )
            except Exception:
                logger.exception(
                    "Failed to refresh thumbnail for project {} page {}",
                    project_id,
                    outline_page.page_number,
                )

            await _safe_send_event(
                sse_manager,
                project_id,
                "page_complete",
                {
                    "page_number": outline_page.page_number,
                    "title": outline_page.title,
                    "status": "generated",
                    "version": getattr(saved_page, "version", None),
                    "vue_code": page_code,
                },
                stream_id=stream_id,
            )

        await project_service.update_project(
            project_id,
            ProjectUpdate(status=ProjectStatus.EDITING),
        )
    except asyncio.CancelledError:
        cancelled = True
        logger.info("Confirm outline stream was cancelled for project {}", project_id)
        raise
    except ProjectNotFoundError as exc:
        await _safe_send_event(
            sse_manager,
            project_id,
            "error",
            {"message": str(exc)},
            stream_id=stream_id,
        )
    except Exception as exc:
        logger.exception("Confirm outline SSE flow failed for project {}", project_id)
        await _safe_send_event(
            sse_manager,
            project_id,
            "error",
            {
                "message": f"确认大纲失败：{str(exc) or exc.__class__.__name__}",
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


def _build_confirm_outline_message(outline: OutlineSchema) -> str:
    return (
        f"已确认《{outline.title}》的 {outline.total_pages} 页大纲。"
        "现在开始逐页生成，请切换到预览模式查看实时结果。"
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


async def _persist_assistant_message(
    *,
    chat_service: ChatService,
    project_id: str,
    final_state: dict[str, object],
) -> None:
    payload = final_state.get("persistable_assistant_message")
    if not isinstance(payload, dict):
        return

    await chat_service.create_message(
        project_id=project_id,
        role=str(payload.get("role") or "assistant"),
        content=str(payload.get("content") or ""),
        message_type=str(payload.get("message_type") or "text"),
        page_number=payload.get("page_number") if isinstance(payload.get("page_number"), int) else None,
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None,
    )
