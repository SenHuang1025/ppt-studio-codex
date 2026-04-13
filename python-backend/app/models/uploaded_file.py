from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import FileParseStatus

if TYPE_CHECKING:
    from app.models.project import Project


class UploadedFile(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "uploaded_files"
    __table_args__ = (
        Index("ix_uploaded_files_project_id", "project_id"),
        Index("ix_uploaded_files_parse_status", "parse_status"),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parsed_content: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    parse_status: Mapped[FileParseStatus] = mapped_column(
        SAEnum(
            FileParseStatus,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=FileParseStatus.PENDING,
        server_default=text("'pending'"),
    )

    project: Mapped["Project"] = relationship(back_populates="uploaded_files")
