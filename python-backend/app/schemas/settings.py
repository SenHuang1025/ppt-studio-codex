from __future__ import annotations

from enum import Enum

from pydantic import Field, field_validator

from app.schemas.base import APIModel


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"


class AppTheme(str, Enum):
    WARM_PAPER = "warm-paper"
    SOFT_FOREST = "soft-forest"


class SettingsResponse(APIModel):
    llm_provider: LLMProvider
    model_name: str
    api_base_url: str
    default_theme: AppTheme
    storage_path: str


class SettingsUpdate(APIModel):
    llm_provider: LLMProvider | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=255)
    api_base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    default_theme: AppTheme | None = None

    @field_validator("model_name")
    @classmethod
    def normalize_model_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            raise ValueError("Model name cannot be blank.")

        return normalized

    @field_validator("api_base_url")
    @classmethod
    def normalize_api_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            raise ValueError("API base URL cannot be blank.")

        return normalized
