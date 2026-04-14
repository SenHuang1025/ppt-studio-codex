from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sse_starlette import EventSourceResponse

from app.agents import API_KEY_HEADER, AgentGraphContext, build_llm_runtime, run_agent_workflow
from app.agents.llm import LLMConfigurationError, MissingAPIKeyError
from app.api.chat import get_chat_service
from app.api.files import get_file_service
from app.api.projects import get_project_service
from app.api.settings import get_settings_service
from app.schemas import AgentChatRequest, AgentConfirmOutlineRequest, OutlineSchema
from app.services import ChatService, FileService, ProjectNotFoundError, ProjectService, SSEManager, SettingsService

router = APIRouter(prefix="/api/projects/{project_id}/agent", tags=["agent"])


def get_sse_manager(request: Request) -> SSEManager:
    sse_manager = getattr(request.app.state, "sse_manager", None)
    if not isinstance(sse_manager, SSEManager):
        raise RuntimeError("SSE manager is not initialized on the FastAPI application.")
    return sse_manager


def _raise_agent_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (MissingAPIKeyError, LLMConfigurationError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.post("/chat")
async def chat_with_agent(
    project_id: str,
    payload: AgentChatRequest,
    request: Request,
    file_service: FileService = Depends(get_file_service),
    chat_service: ChatService = Depends(get_chat_service),
    project_service: ProjectService = Depends(get_project_service),
    settings_service: SettingsService = Depends(get_settings_service),
    sse_manager: SSEManager = Depends(get_sse_manager),
) -> EventSourceResponse:
    api_key = request.headers.get(API_KEY_HEADER, "").strip()

    try:
        llm_runtime = await build_llm_runtime(
            settings_service=settings_service,
            api_key=api_key,
        )
    except Exception as exc:
        _raise_agent_http_error(exc)

    stream_id, stream = await sse_manager.open_stream(project_id)

    async def stream_response() -> AsyncGenerator[object, None]:
        producer_task = asyncio.create_task(
            _produce_agent_events(
                file_service=file_service,
                chat_service=chat_service,
                project_id=project_id,
                project_service=project_service,
                request_payload=payload,
                sse_manager=sse_manager,
                stream_id=stream_id,
                llm_runtime=llm_runtime,
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


@router.post("/confirm-outline")
async def confirm_outline(
    project_id: str,
    payload: AgentConfirmOutlineRequest,
    request: Request,
    chat_service: ChatService = Depends(get_chat_service),
    project_service: ProjectService = Depends(get_project_service),
    sse_manager: SSEManager = Depends(get_sse_manager),
) -> EventSourceResponse:
    stream_id, stream = await sse_manager.open_stream(project_id)

    async def stream_response() -> AsyncGenerator[object, None]:
        producer_task = asyncio.create_task(
            _produce_confirm_outline_events(
                chat_service=chat_service,
                project_id=project_id,
                project_service=project_service,
                request_payload=payload,
                sse_manager=sse_manager,
                stream_id=stream_id,
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


async def _produce_agent_events(
    *,
    chat_service: ChatService,
    file_service: FileService,
    project_id: str,
    project_service: ProjectService,
    request_payload: AgentChatRequest,
    sse_manager: SSEManager,
    stream_id: str,
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
                project_service=project_service,
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
    project_id: str,
    project_service: ProjectService,
    request_payload: AgentConfirmOutlineRequest,
    sse_manager: SSEManager,
    stream_id: str,
) -> None:
    cancelled = False

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
        await project_service.save_outline(project_id, outline_schema)

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
        "预览模式已切换；正式页面生成将在后续阶段接入。"
    )


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
