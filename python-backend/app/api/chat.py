from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.schemas import ChatMessageListResponse
from app.services import ChatService, ChatServiceError, ChatStorageError, ProjectNotFoundError

router = APIRouter(prefix="/api/projects/{project_id}/chat", tags=["chat"])


def get_chat_service(
    session: AsyncSession = Depends(get_db_session),
) -> ChatService:
    return ChatService(session=session)


def _raise_chat_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, ProjectNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ChatStorageError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    if isinstance(exc, ChatServiceError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/messages", response_model=ChatMessageListResponse)
async def list_chat_messages(
    project_id: str,
    page_number: int | None = Query(default=None, ge=1),
    include_global: bool = Query(default=False),
    include_page_messages: bool = Query(default=False),
    limit: int | None = Query(default=None, ge=1, le=200),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatMessageListResponse:
    try:
        messages, total = await chat_service.list_messages(
            project_id,
            page_number=page_number,
            include_page_messages=include_page_messages,
            limit=limit,
            include_global_for_page=include_global,
        )
    except Exception as exc:
        _raise_chat_http_error(exc)

    return ChatMessageListResponse(messages=messages, total=total)
