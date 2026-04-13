from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import ChatMessageType, ChatRole

if TYPE_CHECKING:
    from app.models.project import Project


class ChatMessage(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_project_id", "project_id"),
        Index("ix_chat_messages_project_id_page_number", "project_id", "page_number"),
        Index("ix_chat_messages_created_at", "created_at"),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[ChatRole] = mapped_column(
        SAEnum(ChatRole, native_enum=False, validate_strings=True),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[ChatMessageType] = mapped_column(
        SAEnum(ChatMessageType, native_enum=False, validate_strings=True),
        nullable=False,
        default=ChatMessageType.TEXT,
        server_default=text("'text'"),
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="chat_messages")
