from __future__ import annotations

import asyncio

import pytest

from app.agents.llm import LLMRuntimeConfig, MissingAPIKeyError, build_llm_runtime, create_chat_model
from app.schemas import AppTheme, LLMProvider, SettingsResponse


class FakeSettingsService:
    def __init__(self, settings: SettingsResponse) -> None:
        self._settings = settings

    async def get_settings(self) -> SettingsResponse:
        return self._settings


def build_settings(*, provider: LLMProvider = LLMProvider.OPENAI) -> SettingsResponse:
    return SettingsResponse(
        llm_provider=provider,
        model_name="fake-model",
        api_base_url="https://example.com/v1",
        multi_agent_deliberation_enabled=False,
        default_theme=AppTheme.WARM_PAPER,
        storage_path="E:/tmp/projects",
    )


def test_build_llm_runtime_requires_api_key() -> None:
    settings_service = FakeSettingsService(build_settings())

    with pytest.raises(MissingAPIKeyError) as exc_info:
        asyncio.run(build_llm_runtime(settings_service=settings_service, api_key="   "))

    assert "API Key" in str(exc_info.value)
    assert "sk-" not in str(exc_info.value)


def test_create_chat_model_uses_openai_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_config: list[LLMRuntimeConfig] = []

    def fake_factory(config: LLMRuntimeConfig) -> object:
        captured_config.append(config)
        return object()

    monkeypatch.setattr("app.agents.llm._create_openai_chat_model", fake_factory)

    runtime_config = LLMRuntimeConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-test",
        api_base_url="https://example.com/v1",
        api_key="test-key",
        deliberation_enabled=False,
    )

    model = create_chat_model(runtime_config)

    assert model is not None
    assert captured_config == [runtime_config]


def test_create_chat_model_uses_anthropic_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_config: list[LLMRuntimeConfig] = []

    def fake_factory(config: LLMRuntimeConfig) -> object:
        captured_config.append(config)
        return object()

    monkeypatch.setattr("app.agents.llm._create_anthropic_chat_model", fake_factory)

    runtime_config = LLMRuntimeConfig(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-test",
        api_base_url="https://anthropic.example.com",
        api_key="test-key",
        deliberation_enabled=True,
    )

    model = create_chat_model(runtime_config)

    assert model is not None
    assert captured_config == [runtime_config]
