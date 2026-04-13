from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import APIModel, ORMModel
from app.schemas.enums import FileParseStatus


class UploadedFileResponse(ORMModel):
    id: str
    project_id: str
    original_name: str
    file_type: str
    file_path: str
    file_size: int | None = None
    parsed_content: dict[str, Any] | None = None
    parse_status: FileParseStatus
    created_at: datetime


class UploadedFileListResponse(APIModel):
    files: list[UploadedFileResponse] = Field(default_factory=list)


class UploadedFileDeleteResponse(APIModel):
    success: bool = True


class ParsedFileResponse(APIModel):
    file_id: str
    parsed_content: dict[str, Any] | None = None
    status: FileParseStatus
