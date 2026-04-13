from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import APIModel, ORMModel
from app.schemas.enums import ChatMessageType, ChatRole


class ChatMessageCreate(APIModel):
    content: str = Field(min_length=1)
    page_number: int | None = None


class AgentChatRequest(APIModel):
    message: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)


class ChatMessageResponse(ORMModel):
    id: str
    project_id: str
    page_number: int | None = None
    role: ChatRole
    content: str
    message_type: ChatMessageType
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_json")
    created_at: datetime


class SSEEvent(APIModel):
    event: str
    data: dict[str, Any] = Field(default_factory=dict)
