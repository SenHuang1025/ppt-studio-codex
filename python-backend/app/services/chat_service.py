from __future__ import annotations

from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, ChatMessageType, ChatRole, Project
from app.services.project_service import ProjectNotFoundError


class ChatServiceError(Exception):
    """Base exception for chat service failures."""


class ChatMessageNotFoundError(ChatServiceError):
    def __init__(self, project_id: str, message_id: str):
        super().__init__(f"Chat message '{message_id}' was not found in project '{project_id}'.")
        self.project_id = project_id
        self.message_id = message_id


class ChatStorageError(ChatServiceError):
    """Raised when chat message persistence fails."""


class ChatService:
    DEFAULT_AGENT_HISTORY_LIMIT = 20

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_message(
        self,
        *,
        project_id: str,
        role: ChatRole | str,
        content: str,
        message_type: ChatMessageType | str = ChatMessageType.TEXT,
        page_number: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessage:
        await self._ensure_project_exists(project_id)
        normalized_content = content.strip()
        if not normalized_content:
            raise ChatServiceError("Chat message content cannot be blank.")
        if page_number is not None and page_number < 1:
            raise ChatServiceError("Chat message page_number must be greater than or equal to 1.")

        message = ChatMessage(
            project_id=project_id,
            page_number=page_number,
            role=ChatRole(role),
            content=normalized_content,
            message_type=ChatMessageType(message_type),
            metadata_json=metadata,
        )
        self.session.add(message)

        try:
            await self.session.commit()
            await self.session.refresh(message)
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise ChatStorageError(f"Failed to persist chat message for project '{project_id}'.") from exc

        return message

    async def list_messages(
        self,
        project_id: str,
        *,
        page_number: int | None = None,
        limit: int | None = None,
        include_global_for_page: bool = False,
        exclude_message_id: str | None = None,
    ) -> tuple[list[ChatMessage], int]:
        await self._ensure_project_exists(project_id)
        if page_number is not None and page_number < 1:
            raise ChatServiceError("Chat history page_number must be greater than or equal to 1.")
        if limit is not None and limit < 1:
            raise ChatServiceError("Chat history limit must be greater than or equal to 1.")

        filters = self._build_filters(
            project_id=project_id,
            page_number=page_number,
            include_global_for_page=include_global_for_page,
            exclude_message_id=exclude_message_id,
        )

        try:
            total = int(
                (
                    await self.session.execute(
                        select(func.count()).select_from(ChatMessage).where(*filters),
                    )
                ).scalar_one()
            )
            stmt = self._build_list_statement(filters=filters, limit=limit)
            messages = list((await self.session.execute(stmt)).scalars().all())
        except SQLAlchemyError as exc:
            raise ChatStorageError(f"Failed to list chat messages for project '{project_id}'.") from exc

        return messages, total

    async def build_agent_history(
        self,
        project_id: str,
        *,
        page_number: int | None = None,
        limit: int = DEFAULT_AGENT_HISTORY_LIMIT,
        exclude_message_id: str | None = None,
    ) -> list[dict[str, Any]]:
        messages, _ = await self.list_messages(
            project_id,
            page_number=page_number,
            limit=limit,
            include_global_for_page=page_number is not None,
            exclude_message_id=exclude_message_id,
        )
        return [self._serialize_agent_history_message(message) for message in messages]

    async def _ensure_project_exists(self, project_id: str) -> None:
        stmt = select(Project.id).where(Project.id == project_id)
        project_id_in_db = (await self.session.execute(stmt)).scalar_one_or_none()
        if project_id_in_db is None:
            raise ProjectNotFoundError(project_id)

    def _build_filters(
        self,
        *,
        project_id: str,
        page_number: int | None,
        include_global_for_page: bool,
        exclude_message_id: str | None,
    ) -> list[Any]:
        filters: list[Any] = [ChatMessage.project_id == project_id]

        if page_number is None:
            filters.append(ChatMessage.page_number.is_(None))
        elif include_global_for_page:
            filters.append(or_(ChatMessage.page_number == page_number, ChatMessage.page_number.is_(None)))
        else:
            filters.append(ChatMessage.page_number == page_number)

        if exclude_message_id:
            filters.append(ChatMessage.id != exclude_message_id)

        return filters

    def _build_list_statement(self, *, filters: list[Any], limit: int | None) -> Select[tuple[ChatMessage]]:
        if limit is None:
            return select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())

        normalized_limit = max(1, int(limit))
        recent_message_ids = (
            select(ChatMessage.id)
            .where(*filters)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(normalized_limit)
            .subquery()
        )
        return (
            select(ChatMessage)
            .join(recent_message_ids, ChatMessage.id == recent_message_ids.c.id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )

    def _serialize_agent_history_message(self, message: ChatMessage) -> dict[str, Any]:
        metadata = self._serialize_agent_history_metadata(message)
        role = getattr(message.role, "value", message.role)
        message_type = getattr(message.message_type, "value", message.message_type)
        return {
            "role": role,
            "content": message.content,
            "message_type": message_type,
            "page_number": message.page_number,
            "metadata": metadata,
        }

    def _serialize_agent_history_metadata(self, message: ChatMessage) -> dict[str, Any] | None:
        metadata = message.metadata_json
        if not isinstance(metadata, dict):
            return None

        if message.message_type != ChatMessageType.OUTLINE:
            return metadata

        outline = metadata.get("outline")
        if not isinstance(outline, dict):
            return metadata

        pages = outline.get("pages")
        page_titles = []
        if isinstance(pages, list):
            for page in pages[:5]:
                if isinstance(page, dict) and isinstance(page.get("title"), str):
                    page_titles.append(page["title"])

        return {
            "outline_title": outline.get("title"),
            "page_titles": page_titles,
            "theme_suggestion": outline.get("theme_suggestion"),
            "total_pages": outline.get("total_pages"),
        }
