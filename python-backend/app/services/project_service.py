from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.models import ChatMessage, Project
from app.schemas import OutlineSchema, ProjectCreate, ProjectStatus, ProjectUpdate, ThemeConfig


class ProjectServiceError(Exception):
    """Base exception for project service failures."""


class ProjectNotFoundError(ProjectServiceError):
    def __init__(self, project_id: str):
        super().__init__(f"Project '{project_id}' was not found.")
        self.project_id = project_id


class ProjectStorageError(ProjectServiceError):
    """Raised when local project directory management fails."""


class ProjectService:
    PROJECT_SUBDIRECTORIES: tuple[str, ...] = (
        "uploads",
        "parsed",
        "pages",
        "versions",
        "thumbnails",
        "exports",
    )
    SORT_FIELDS = {
        "updated_at": Project.updated_at,
        "created_at": Project.created_at,
        "name": Project.name,
    }
    DEFAULT_SORT = "updated_at"
    DEFAULT_ORDER = "desc"

    def __init__(self, session: AsyncSession, settings: Settings):
        self.session = session
        self.settings = settings

    async def list_projects(
        self,
        *,
        status: ProjectStatus | None = None,
        sort: str | None = None,
        order: str | None = None,
    ) -> tuple[list[Project], int]:
        filters = []
        if status is not None:
            filters.append(Project.status == status)

        count_stmt = select(func.count()).select_from(Project)
        if filters:
            count_stmt = count_stmt.where(*filters)

        query_stmt: Select[tuple[Project]] = select(Project)
        if filters:
            query_stmt = query_stmt.where(*filters)
        query_stmt = query_stmt.order_by(*self._build_order_by(sort=sort, order=order))

        total = int((await self.session.execute(count_stmt)).scalar_one())
        projects = list((await self.session.execute(query_stmt)).scalars().all())
        for project in projects:
            self._attach_thumbnail_metadata(project)
        return projects, total

    async def create_project(self, payload: ProjectCreate) -> Project:
        project = Project(
            name=payload.name,
            description=payload.description,
        )
        self.session.add(project)

        try:
            await self.session.flush()
            await asyncio.to_thread(self._create_project_directories, project.id)
            await self.session.commit()
            await self.session.refresh(project)
        except (OSError, SQLAlchemyError) as exc:
            await self.session.rollback()
            if project.id:
                await asyncio.to_thread(self._cleanup_project_directories, project.id)
            raise ProjectStorageError(
                f"Failed to create project '{payload.name}'.",
            ) from exc

        logger.info("Created project {} at {}", project.id, self.settings.project_dir(project.id))
        self._attach_thumbnail_metadata(project)
        return project

    async def get_project_detail(self, project_id: str) -> Project:
        project = await self._get_project_or_raise(project_id, include_pages=True)
        page_message_counts = await self._count_page_messages(project_id)
        self._attach_thumbnail_metadata(project)
        for page in getattr(project, "pages", []) or []:
            setattr(page, "chat_message_count", int(page_message_counts.get(int(page.page_number), 0)))
            setattr(
                page,
                "thumbnail_updated_at",
                self._resolve_thumbnail_updated_at(
                    project_id=project_id,
                    page_number=int(page.page_number),
                ),
            )
        return project

    async def update_project(self, project_id: str, payload: ProjectUpdate) -> Project:
        project = await self._get_project_or_raise(project_id)
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return project

        for field_name, value in changes.items():
            setattr(project, field_name, value)

        try:
            await self.session.commit()
            await self.session.refresh(project)
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise ProjectStorageError(
                f"Failed to update project '{project_id}'.",
            ) from exc

        logger.info("Updated project {}", project_id)
        self._attach_thumbnail_metadata(project)
        return project

    async def save_outline(self, project_id: str, outline: OutlineSchema | dict[str, object]) -> Project:
        project = await self._get_project_or_raise(project_id)
        outline_schema = outline if isinstance(outline, OutlineSchema) else OutlineSchema.model_validate(outline)
        project.outline = outline_schema.model_dump(mode="json")
        project.total_pages = outline_schema.total_pages
        project.status = ProjectStatus.PLANNING

        try:
            await self.session.commit()
            await self.session.refresh(project)
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise ProjectStorageError(
                f"Failed to persist outline for project '{project_id}'.",
            ) from exc

        logger.info("Saved outline for project {}", project_id)
        self._attach_thumbnail_metadata(project)
        return project

    async def save_theme_config(
        self,
        project_id: str,
        theme_config: ThemeConfig | dict[str, object],
    ) -> Project:
        project = await self._get_project_or_raise(project_id)
        theme_schema = (
            theme_config if isinstance(theme_config, ThemeConfig) else ThemeConfig.model_validate(theme_config)
        )
        project.theme_config = theme_schema.model_dump(mode="json")

        try:
            await self.session.commit()
            await self.session.refresh(project)
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise ProjectStorageError(
                f"Failed to persist theme for project '{project_id}'.",
            ) from exc

        logger.info("Saved theme config for project {}", project_id)
        self._attach_thumbnail_metadata(project)
        return project

    async def delete_project(self, project_id: str) -> None:
        project = await self._get_project_or_raise(project_id)
        await self.session.delete(project)

        try:
            await asyncio.to_thread(self._delete_project_directories, project_id)
            await self.session.commit()
        except (OSError, SQLAlchemyError) as exc:
            await self.session.rollback()
            raise ProjectStorageError(
                f"Failed to delete project '{project_id}'.",
            ) from exc

        logger.info("Deleted project {}", project_id)

    async def _get_project_or_raise(self, project_id: str, *, include_pages: bool = False) -> Project:
        stmt: Select[tuple[Project]] = select(Project).where(Project.id == project_id)
        if include_pages:
            stmt = stmt.options(selectinload(Project.pages))

        project = (await self.session.execute(stmt)).scalar_one_or_none()
        if project is None:
            raise ProjectNotFoundError(project_id)
        return project

    async def _count_page_messages(self, project_id: str) -> dict[int, int]:
        stmt = (
            select(ChatMessage.page_number, func.count(ChatMessage.id))
            .where(
                ChatMessage.project_id == project_id,
                ChatMessage.page_number.is_not(None),
            )
            .group_by(ChatMessage.page_number)
        )

        rows = (await self.session.execute(stmt)).all()
        counts: dict[int, int] = {}
        for page_number, count in rows:
            if isinstance(page_number, int):
                counts[page_number] = int(count or 0)
        return counts

    def _build_order_by(self, *, sort: str | None, order: str | None) -> list:
        sort_key = (sort or self.DEFAULT_SORT).strip().lower()
        order_key = (order or self.DEFAULT_ORDER).strip().lower()

        sort_column = self.SORT_FIELDS.get(sort_key, self.SORT_FIELDS[self.DEFAULT_SORT])
        primary_order = sort_column.asc() if order_key == "asc" else sort_column.desc()
        return [primary_order, Project.updated_at.desc(), Project.id.desc()]

    def _project_root(self) -> Path:
        return self.settings.projects_dir.resolve()

    def _validated_project_dir(self, project_id: str) -> Path:
        project_root = self._project_root()
        project_dir = self.settings.project_dir(project_id).resolve()
        if not project_dir.is_relative_to(project_root):
            raise ProjectStorageError(f"Unsafe project path resolved for '{project_id}'.")
        if project_dir.parent != project_root or project_dir.name != project_id:
            raise ProjectStorageError(f"Refusing to operate on unexpected project path '{project_dir}'.")
        return project_dir

    def _create_project_directories(self, project_id: str) -> None:
        project_root = self._project_root()
        project_root.mkdir(parents=True, exist_ok=True)

        project_dir = self._validated_project_dir(project_id)
        try:
            project_dir.mkdir(parents=False, exist_ok=False)
            for subdirectory in self.PROJECT_SUBDIRECTORIES:
                (project_dir / subdirectory).mkdir(parents=False, exist_ok=False)
        except OSError:
            self._cleanup_project_directories(project_id)
            raise

    def _delete_project_directories(self, project_id: str) -> None:
        project_dir = self._validated_project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)

    def _cleanup_project_directories(self, project_id: str) -> None:
        project_dir = self._validated_project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)

    def _attach_thumbnail_metadata(self, project: Project) -> None:
        setattr(
            project,
            "first_thumbnail_updated_at",
            self._resolve_thumbnail_updated_at(project_id=project.id, page_number=1),
        )

    def _resolve_thumbnail_updated_at(self, *, project_id: str, page_number: int) -> datetime | None:
        thumbnail_path = self.settings.project_dir(project_id) / "thumbnails" / f"page-{page_number}.png"
        try:
            stat_result = thumbnail_path.stat()
        except OSError:
            return None

        return datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc)
