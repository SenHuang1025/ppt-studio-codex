from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.settings import router as settings_router
from app.config import Settings, get_settings
from app.db import get_db_session


def test_settings_api_returns_defaults_including_deliberation_flag(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app = build_test_app(settings=settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.get("/api/settings")

    payload = response.json()

    assert response.status_code == 200
    assert payload["llm_provider"] == "openai"
    assert payload["model_name"] == "gpt-5.2"
    assert payload["api_base_url"] == "https://api.openai.com/v1"
    assert payload["multi_agent_deliberation_enabled"] is False
    assert payload["default_theme"] == "warm-paper"
    assert payload["storage_path"] == str(settings.projects_dir)


def test_settings_api_updates_and_persists_deliberation_flag(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app = build_test_app(settings=settings, session_factory=session_factory)

    with TestClient(app) as client:
        update_response = client.put(
            "/api/settings",
            json={
                "llm_provider": "anthropic",
                "model_name": "claude-sonnet-4-20250514",
                "api_base_url": "https://example.com/v1",
                "multi_agent_deliberation_enabled": True,
                "default_theme": "soft-forest",
            },
        )
        get_response = client.get("/api/settings")

    update_payload = update_response.json()
    get_payload = get_response.json()

    assert update_response.status_code == 200
    assert update_payload["multi_agent_deliberation_enabled"] is True
    assert update_payload["llm_provider"] == "anthropic"
    assert update_payload["model_name"] == "claude-sonnet-4-20250514"
    assert update_payload["api_base_url"] == "https://example.com/v1"
    assert update_payload["default_theme"] == "soft-forest"

    assert get_response.status_code == 200
    assert get_payload["multi_agent_deliberation_enabled"] is True
    assert get_payload["llm_provider"] == "anthropic"
    assert get_payload["model_name"] == "claude-sonnet-4-20250514"
    assert get_payload["api_base_url"] == "https://example.com/v1"
    assert get_payload["default_theme"] == "soft-forest"


def build_test_app(*, settings: Settings, session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    app = FastAPI()
    app.include_router(settings_router)

    async def override_db_session() -> Any:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings
    return app
