from __future__ import annotations

from enum import Enum
from typing import TypeVar

from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Setting
from app.schemas import AppTheme, LLMProvider, SettingsResponse, SettingsUpdate

TEnum = TypeVar("TEnum", bound=Enum)


class SettingsServiceError(Exception):
    """Raised when settings persistence fails."""


class SettingsService:
    MANAGED_KEYS: tuple[str, ...] = (
        "llm_provider",
        "model_name",
        "api_base_url",
        "default_theme",
    )
    DEFAULT_VALUES = {
        "llm_provider": LLMProvider.OPENAI.value,
        "model_name": "gpt-5.2",
        "api_base_url": "https://api.openai.com/v1",
        "default_theme": AppTheme.WARM_PAPER.value,
    }

    def __init__(self, session: AsyncSession, settings: Settings):
        self.session = session
        self.settings = settings

    async def get_settings(self) -> SettingsResponse:
        values = await self._load_values()
        return self._build_response(values)

    async def update_settings(self, payload: SettingsUpdate) -> SettingsResponse:
        changes = payload.model_dump(exclude_unset=True, mode="json")
        if not changes:
            return await self.get_settings()

        existing_settings = await self._load_setting_models()

        for key, value in changes.items():
            normalized_value = self._normalize_value(value)
            setting = existing_settings.get(key)

            if setting is None:
                self.session.add(Setting(key=key, value=normalized_value))
                continue

            setting.value = normalized_value

        try:
            await self.session.commit()
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise SettingsServiceError("Failed to persist settings.") from exc

        return await self.get_settings()

    async def _load_values(self) -> dict[str, str]:
        settings = await self._load_setting_models()
        return {key: item.value for key, item in settings.items()}

    async def _load_setting_models(self) -> dict[str, Setting]:
        stmt: Select[tuple[Setting]] = select(Setting).where(Setting.key.in_(self.MANAGED_KEYS))
        rows = (await self.session.execute(stmt)).scalars().all()
        return {item.key: item for item in rows}

    def _build_response(self, values: dict[str, str]) -> SettingsResponse:
        return SettingsResponse(
            llm_provider=self._coerce_enum(
                enum_cls=LLMProvider,
                raw_value=values.get("llm_provider"),
                default=LLMProvider.OPENAI,
            ),
            model_name=self._coerce_string("model_name", values.get("model_name")),
            api_base_url=self._coerce_string("api_base_url", values.get("api_base_url")),
            default_theme=self._coerce_enum(
                enum_cls=AppTheme,
                raw_value=values.get("default_theme"),
                default=AppTheme.WARM_PAPER,
            ),
            storage_path=str(self.settings.projects_dir),
        )

    def _coerce_string(self, key: str, raw_value: str | None) -> str:
        normalized = (raw_value or "").strip()
        if normalized:
            return normalized
        return self.DEFAULT_VALUES[key]

    def _coerce_enum(self, *, enum_cls: type[TEnum], raw_value: str | None, default: TEnum) -> TEnum:
        if raw_value is None:
            return default

        try:
            return enum_cls(raw_value)
        except ValueError:
            return default

    def _normalize_value(self, value: object) -> str:
        if isinstance(value, Enum):
            return str(value.value)
        return str(value).strip()
