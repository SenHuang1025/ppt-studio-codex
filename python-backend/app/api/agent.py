from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from loguru import logger
from sse_starlette import EventSourceResponse

from app.api.files import get_file_service
from app.models import UploadedFile
from app.models.enums import FileParseStatus
from app.schemas import AgentChatRequest
from app.services import FileService, SSEManager

router = APIRouter(prefix="/api/projects/{project_id}/agent", tags=["agent"])


def get_sse_manager(request: Request) -> SSEManager:
    sse_manager = getattr(request.app.state, "sse_manager", None)
    if not isinstance(sse_manager, SSEManager):
        raise RuntimeError("SSE manager is not initialized on the FastAPI application.")
    return sse_manager


@router.post("/chat")
async def chat_with_agent(
    project_id: str,
    payload: AgentChatRequest,
    request: Request,
    file_service: FileService = Depends(get_file_service),
    sse_manager: SSEManager = Depends(get_sse_manager),
) -> EventSourceResponse:
    stream_id, stream = await sse_manager.open_stream(project_id)

    async def stream_response() -> AsyncGenerator[object, None]:
        producer_task = asyncio.create_task(
            _produce_agent_events(
                file_service=file_service,
                project_id=project_id,
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
    file_service: FileService,
    project_id: str,
    request_payload: AgentChatRequest,
    sse_manager: SSEManager,
    stream_id: str,
) -> None:
    cancelled = False

    try:
        await sse_manager.send_event(
            project_id,
            "thinking",
            {
                "agent": "system",
                "content": "正在建立实时会话...",
            },
            stream_id=stream_id,
        )

        uploaded_files = await file_service.list_files(project_id)
        parsed_count = 0
        parse_error_count = 0

        for uploaded_file in uploaded_files:
            if not _should_parse_file(uploaded_file):
                continue

            try:
                parsed_file = await file_service.parse_file(project_id, uploaded_file.id)
            except Exception as exc:
                parse_error_count += 1
                logger.exception(
                    "Failed to parse uploaded file {} during agent chat for project {}",
                    uploaded_file.id,
                    project_id,
                )
                await _safe_send_event(
                    sse_manager,
                    project_id,
                    "error",
                    {
                        "message": f"文件 {uploaded_file.original_name} 解析失败：{str(exc) or exc.__class__.__name__}",
                    },
                    stream_id=stream_id,
                )
                continue

            parsed_count += 1
            await sse_manager.send_event(
                project_id,
                "file_parsed",
                {
                    "file_id": parsed_file.id,
                    "file_name": parsed_file.original_name,
                    "summary": _extract_file_summary(parsed_file),
                },
                stream_id=stream_id,
            )

        await sse_manager.send_event(
            project_id,
            "assistant_message",
            {
                "content": _build_assistant_message(
                    user_message=request_payload.message,
                    checked_file_count=len(uploaded_files),
                    parsed_file_count=parsed_count,
                    parse_error_count=parse_error_count,
                )
            },
            stream_id=stream_id,
        )
    except asyncio.CancelledError:
        cancelled = True
        logger.info("Agent chat stream was cancelled for project {}", project_id)
        raise
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


def _should_parse_file(uploaded_file: UploadedFile) -> bool:
    if uploaded_file.parse_status in {FileParseStatus.PENDING, FileParseStatus.FAILED}:
        return True

    return uploaded_file.parse_status == FileParseStatus.PARSED and uploaded_file.parsed_content is None


def _extract_file_summary(uploaded_file: UploadedFile) -> str:
    parsed_content = uploaded_file.parsed_content
    if parsed_content and isinstance(parsed_content.get("summary"), str):
        summary = parsed_content["summary"].strip()
        if summary:
            return summary

    return f"{uploaded_file.original_name} 已完成解析。"


def _build_assistant_message(
    *,
    user_message: str,
    checked_file_count: int,
    parsed_file_count: int,
    parse_error_count: int,
) -> str:
    parts = [
        "SSE 已接通。",
        f"已收到你的消息：{user_message.strip()}。",
        f"本次共检查 {checked_file_count} 个文件，新增解析 {parsed_file_count} 个文件。",
    ]

    if parse_error_count > 0:
        parts.append(f"其中 {parse_error_count} 个文件解析失败，请查看上方错误事件。")

    parts.append("真正的 Agent 路由和大纲规划会在 Phase 2 的 2.4 接入。")
    return " ".join(parts)


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
