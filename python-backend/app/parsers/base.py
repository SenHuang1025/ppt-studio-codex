from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ParseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_type: str
    summary: str
    text_content: str
    structured_data: dict[str, Any] = Field(default_factory=dict)
    key_points: list[str] = Field(default_factory=list)


class BaseParser(ABC):
    @abstractmethod
    async def parse(self, file_path: str) -> ParseResult:
        """Parse a file and return a JSON-serializable result."""
