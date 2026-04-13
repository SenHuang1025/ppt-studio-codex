from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PageStatus

if TYPE_CHECKING:
    from app.models.project import Project


class ProjectPage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_pages"
    __table_args__ = (
        UniqueConstraint("project_id", "page_number", name="uq_project_pages_project_id_page_number"),
        Index("ix_project_pages_project_id", "project_id"),
        Index("ix_project_pages_status", "status"),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vue_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PageStatus] = mapped_column(
        SAEnum(PageStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=PageStatus.PLANNED,
        server_default=text("'planned'"),
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    project: Mapped["Project"] = relationship(back_populates="pages")
    versions: Mapped[list["PageVersion"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PageVersion.version",
    )


class PageVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "page_versions"
    __table_args__ = (
        UniqueConstraint("page_id", "version", name="uq_page_versions_page_id_version"),
        Index("ix_page_versions_page_id", "page_id"),
    )

    page_id: Mapped[str] = mapped_column(
        ForeignKey("project_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    vue_code: Mapped[str] = mapped_column(Text, nullable=False)
    change_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    page: Mapped["ProjectPage"] = relationship(back_populates="versions")
