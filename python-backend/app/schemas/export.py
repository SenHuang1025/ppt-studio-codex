from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.schemas.base import APIModel


class ProjectExportFormat(StrEnum):
    PDF = "pdf"


class ProjectExportStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectExportTaskResponse(APIModel):
    id: str
    project_id: str
    format: ProjectExportFormat
    status: ProjectExportStatus
    stage: str
    total_pages: int = Field(ge=0)
    completed_pages: int = Field(ge=0)
    current_page_number: int | None = Field(default=None, ge=1)
    current_page_title: str | None = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    error: str | None = None
    artifact_name: str | None = None
    artifact_size_bytes: int | None = Field(default=None, ge=0)
    download_url: str | None = None
    created_at: datetime
    updated_at: datetime
