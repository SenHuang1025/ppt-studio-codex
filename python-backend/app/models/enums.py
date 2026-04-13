from __future__ import annotations

from enum import Enum


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    GENERATING = "generating"
    EDITING = "editing"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class PageStatus(str, Enum):
    PLANNED = "planned"
    GENERATING = "generating"
    GENERATED = "generated"
    OPTIMIZING = "optimizing"
    CONFIRMED = "confirmed"


class FileParseStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessageType(str, Enum):
    TEXT = "text"
    FILE_UPLOAD = "file_upload"
    OUTLINE = "outline"
    CODE = "code"
    STATUS = "status"
