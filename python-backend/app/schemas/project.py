from __future__ import annotations

from datetime import datetime
from pydantic import Field, field_validator

from app.schemas.base import APIModel, ORMModel
from app.schemas.enums import PageStatus, ProjectStatus
from app.schemas.theme import ThemeConfig


class OutlinePageSchema(APIModel):
    page_number: int
    title: str
    type: str
    content_brief: str
    layout: str
    data_refs: list[str] = Field(default_factory=list)


class OutlineSchema(APIModel):
    title: str
    total_pages: int
    theme_suggestion: str
    pages: list[OutlinePageSchema] = Field(default_factory=list)


class ProjectCreate(APIModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Project name cannot be blank.")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ProjectUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None

    @field_validator("name")
    @classmethod
    def validate_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Project name cannot be blank.")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_optional_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ProjectResponse(ORMModel):
    id: str
    name: str
    description: str | None = None
    status: ProjectStatus
    theme_config: ThemeConfig | None = None
    total_pages: int
    created_at: datetime
    updated_at: datetime


class PageResponse(ORMModel):
    id: str
    project_id: str
    page_number: int
    title: str | None = None
    page_type: str | None = None
    vue_code: str | None = None
    status: PageStatus
    version: int
    created_at: datetime
    updated_at: datetime


class PageVersionResponse(ORMModel):
    id: str
    page_id: str
    version: int
    vue_code: str
    change_description: str | None = None
    created_at: datetime


class ProjectDetailResponse(ProjectResponse):
    outline: OutlineSchema | None = None
    pages: list[PageResponse] = Field(default_factory=list)


class ProjectListResponse(APIModel):
    projects: list[ProjectResponse] = Field(default_factory=list)
    total: int


class ProjectDeleteResponse(APIModel):
    success: bool = True
