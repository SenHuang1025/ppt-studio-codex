from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.projects import router as projects_router
from app.api.themes import router as themes_router
from app.config import Settings, get_settings
from app.db import get_db_session


def test_get_themes_returns_all_presets(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    app = build_test_app(
        settings=settings.model_copy(
            update={"preview_theme_file_override": tmp_path / "preview" / "variables.css"}
        ),
        session_factory=session_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/themes")

    payload = response.json()

    assert response.status_code == 200
    assert [theme["id"] for theme in payload["themes"]] == [
        "warm-orange",
        "business-blue",
        "fresh-green",
        "minimal-gray",
        "tech-dark",
    ]


def test_put_project_theme_persists_theme_and_rewrites_preview_css(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    project_id: str,
    tmp_path: Path,
) -> None:
    preview_theme_file = tmp_path / "preview" / "variables.css"
    app = build_test_app(
        settings=settings.model_copy(update={"preview_theme_file_override": preview_theme_file}),
        session_factory=session_factory,
    )

    with TestClient(app) as client:
        themes_response = client.get("/api/themes")
        business_blue = next(
            theme for theme in themes_response.json()["themes"] if theme["id"] == "business-blue"
        )
        response = client.put(f"/api/projects/{project_id}/theme", json=business_blue)

    payload = response.json()

    assert response.status_code == 200
    assert payload["id"] == project_id
    assert payload["theme_config"]["id"] == "business-blue"
    assert preview_theme_file.read_text(encoding="utf-8").find("--slide-primary: #3b6ea8;") >= 0


def test_sync_project_theme_uses_default_theme_without_touching_database(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    project_id: str,
    tmp_path: Path,
) -> None:
    preview_theme_file = tmp_path / "preview" / "variables.css"
    app = build_test_app(
        settings=settings.model_copy(update={"preview_theme_file_override": preview_theme_file}),
        session_factory=session_factory,
    )

    with TestClient(app) as client:
        detail_before = client.get(f"/api/projects/{project_id}")
        sync_response = client.post(f"/api/projects/{project_id}/theme/sync")
        detail_after = client.get(f"/api/projects/{project_id}")

    before_payload = detail_before.json()
    sync_payload = sync_response.json()
    after_payload = detail_after.json()

    assert detail_before.status_code == 200
    assert sync_response.status_code == 200
    assert detail_after.status_code == 200
    assert before_payload["theme_config"] is None
    assert sync_payload["theme"]["id"] == "warm-orange"
    assert after_payload["theme_config"] is None
    assert "--slide-primary: #68a67d;" in preview_theme_file.read_text(encoding="utf-8")


def build_test_app(*, settings: Settings, session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    app = FastAPI()
    app.include_router(projects_router)
    app.include_router(themes_router)

    async def override_db_session() -> Any:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings
    return app
