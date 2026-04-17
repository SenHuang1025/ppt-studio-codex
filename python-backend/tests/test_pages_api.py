from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sse_starlette.sse import AppStatus

import app.api.pages as pages_api
from app.agents.llm import LLMRuntime, LLMRuntimeConfig
from app.api.pages import router as pages_router
from app.api.projects import router as projects_router
from app.config import Settings, get_settings
from app.db import get_db_session
from app.main import register_exception_handlers
from app.models import PageVersion, ProjectPage, UploadedFile
from app.models.enums import FileParseStatus, PageStatus
from app.schemas import (
    AppTheme,
    LLMProvider,
    OutlinePageSchema,
    OutlineSchema,
    ProjectCreate,
    SettingsResponse,
)
from app.services import ProjectService, SSEManager, ThemeService
from app.services.thumbnail_service import ThumbnailService

VALID_SFC = """
<script setup lang="ts">
const sections = ['营收', '利润率', '计划']
</script>

<template>
  <main class="slide-page">
    <section class="hero">
      <h1>经营亮点</h1>
      <ul>
        <li v-for="item in sections" :key="item">{{ item }}</li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.slide-page {
  width: 1920px;
  height: 1080px;
  overflow: hidden;
  background: var(--slide-bg);
  color: var(--slide-text);
}
</style>
""".strip()


@dataclass
class FakeModelResponse:
    content: str


class FakeChatModel:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[Any] = []

    async def ainvoke(self, messages: Any) -> FakeModelResponse:
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("Fake model ran out of responses.")

        next_response = self.responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response

        return FakeModelResponse(content=next_response)


def test_generate_single_page_returns_400_when_api_key_missing(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    local_settings = build_local_settings(settings)
    app = build_test_app(settings=local_settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.post("/api/projects/project-1/pages/1/generate")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "请先在设置页配置 API Key。"
    assert payload["detail"] == "请先在设置页配置 API Key。"


def test_confirm_page_updates_status_to_confirmed(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    asyncio.run(
        seed_generated_page(
            session_factory=session_factory,
            project_id=project_id,
            page_number=2,
            title="经营亮点",
        )
    )
    app = build_test_app(settings=local_settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.post(f"/api/projects/{project_id}/pages/2/confirm")

    payload = response.json()
    persisted_page = asyncio.run(load_generated_page(session_factory=session_factory, project_id=project_id, page_number=2))

    assert response.status_code == 200
    assert payload["page_number"] == 2
    assert payload["status"] == "confirmed"
    assert persisted_page is not None
    assert persisted_page.status == PageStatus.CONFIRMED


def test_list_page_versions_returns_versions_for_page(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    asyncio.run(
        seed_generated_page(
            session_factory=session_factory,
            project_id=project_id,
            page_number=2,
            title="经营亮点",
        )
    )
    asyncio.run(
        optimize_seed_page(
            session_factory=session_factory,
            settings=local_settings,
            project_id=project_id,
            page_number=2,
        )
    )
    app = build_test_app(settings=local_settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.get(f"/api/projects/{project_id}/pages/2/versions")

    payload = response.json()

    assert response.status_code == 200
    assert [item["version"] for item in payload] == [2, 1]
    assert payload[0]["change_description"] == "标题改为红色"


def test_rollback_page_restores_target_code_and_updates_preview_file(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    asyncio.run(
        seed_generated_page(
            session_factory=session_factory,
            project_id=project_id,
            page_number=2,
            title="经营亮点",
        )
    )
    asyncio.run(
        optimize_seed_page(
            session_factory=session_factory,
            settings=local_settings,
            project_id=project_id,
            page_number=2,
        )
    )
    app = build_test_app(settings=local_settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.post(
            f"/api/projects/{project_id}/pages/2/rollback",
            json={"version": 1},
        )

    payload = response.json()
    persisted_page = asyncio.run(load_generated_page(session_factory=session_factory, project_id=project_id, page_number=2))
    versions = asyncio.run(load_page_versions(session_factory=session_factory, project_id=project_id, page_number=2))
    preview_file = Path(local_settings.preview_slides_dir_path / "page-2.vue").resolve()

    assert response.status_code == 200
    assert payload["page_number"] == 2
    assert payload["version"] == 3
    assert persisted_page is not None
    assert persisted_page.version == 3
    assert persisted_page.vue_code == VALID_SFC
    assert [version.version for version in versions] == [1, 2, 3]
    assert versions[-1].change_description == "回滚到 v1"
    assert preview_file.read_text(encoding="utf-8") == VALID_SFC


def test_get_page_thumbnail_returns_generated_png(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    asyncio.run(
        seed_generated_page(
            session_factory=session_factory,
            project_id=project_id,
            page_number=2,
            title="经营亮点",
        )
    )
    thumbnail_dir = local_settings.project_dir(project_id) / "thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_path = thumbnail_dir / "page-2.png"
    thumbnail_path.write_bytes(b"\x89PNG\r\n\x1a\nfake-thumbnail")
    app = build_test_app(settings=local_settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.get(f"/api/projects/{project_id}/pages/2/thumbnail")
        project_response = client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"\x89PNG\r\n\x1a\nfake-thumbnail"
    assert project_response.status_code == 200
    page_payload = next(page for page in project_response.json()["pages"] if page["page_number"] == 2)
    assert page_payload["thumbnail_updated_at"] is not None


def test_get_page_thumbnail_returns_404_when_missing(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    app = build_test_app(settings=local_settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.get(f"/api/projects/{project_id}/pages/2/thumbnail")

    assert response.status_code == 404


def test_preview_page_version_writes_temporary_preview_file(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    asyncio.run(
        seed_generated_page(
            session_factory=session_factory,
            project_id=project_id,
            page_number=2,
            title="经营亮点",
        )
    )
    asyncio.run(
        optimize_seed_page(
            session_factory=session_factory,
            settings=local_settings,
            project_id=project_id,
            page_number=2,
        )
    )
    app = build_test_app(settings=local_settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.post(f"/api/projects/{project_id}/pages/2/versions/1/preview")

    payload = response.json()
    preview_file = Path(local_settings.preview_slides_dir_path / "version-preview.vue").resolve()

    assert response.status_code == 200
    assert payload["version"] == 1
    assert preview_file.read_text(encoding="utf-8") == VALID_SFC


def test_delete_page_endpoint_removes_page_and_reindexes(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    asyncio.run(seed_all_generated_pages(session_factory=session_factory, settings=local_settings, project_id=project_id))
    app = build_test_app(settings=local_settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.delete(f"/api/projects/{project_id}/pages/2")
        project_response = client.get(f"/api/projects/{project_id}")

    payload = project_response.json()

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert [page["page_number"] for page in payload["pages"]] == [1, 2]
    assert [page["title"] for page in payload["pages"]] == ["封面", "下一步计划"]
    assert payload["outline"]["total_pages"] == 2
    assert [page["page_number"] for page in payload["outline"]["pages"]] == [1, 2]
    assert not (local_settings.preview_slides_dir_path / "page-3.vue").exists()


def test_delete_page_endpoint_schedules_thumbnail_cleanup_for_remaining_pages(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    asyncio.run(seed_all_generated_pages(session_factory=session_factory, settings=local_settings, project_id=project_id))
    thumbnail_dir = local_settings.project_dir(project_id) / "thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    (thumbnail_dir / "page-1.png").write_bytes(b"page-1")
    (thumbnail_dir / "page-2.png").write_bytes(b"page-2")
    (thumbnail_dir / "page-3.png").write_bytes(b"page-3")
    captured_refresh_payloads: list[dict[str, object]] = []

    async def fake_ensure_project_thumbnails(self, *, snapshot, page_numbers=None, cleanup_stale=True):
        expected_page_numbers = [page.page_number for page in snapshot.pages]
        resolved_page_numbers = list(page_numbers or expected_page_numbers)
        captured_refresh_payloads.append(
            {
                "project_id": snapshot.project_id,
                "page_numbers": resolved_page_numbers,
                "expected_page_numbers": expected_page_numbers,
            }
        )
        if cleanup_stale:
            expected = set(expected_page_numbers)
            for thumbnail_path in thumbnail_dir.glob("page-*.png"):
                page_number = int(thumbnail_path.stem.removeprefix("page-"))
                if page_number not in expected:
                    thumbnail_path.unlink()
        return []

    monkeypatch.setattr(ThumbnailService, "ensure_project_thumbnails", fake_ensure_project_thumbnails)
    app = build_test_app(
        settings=local_settings,
        session_factory=session_factory,
        thumbnail_service=ThumbnailService(settings=local_settings),
    )

    with TestClient(app) as client:
        response = client.delete(f"/api/projects/{project_id}/pages/2")

    assert response.status_code == 200
    assert captured_refresh_payloads == [
        {
            "project_id": project_id,
            "page_numbers": [1, 2],
            "expected_page_numbers": [1, 2],
        }
    ]
    assert (thumbnail_dir / "page-1.png").exists()
    assert (thumbnail_dir / "page-2.png").exists()
    assert not (thumbnail_dir / "page-3.png").exists()


def test_duplicate_page_endpoint_inserts_copy_after_current_page(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    asyncio.run(seed_all_generated_pages(session_factory=session_factory, settings=local_settings, project_id=project_id))
    app = build_test_app(settings=local_settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.post(f"/api/projects/{project_id}/pages/2/duplicate")
        project_response = client.get(f"/api/projects/{project_id}")

    payload = project_response.json()

    assert response.status_code == 200
    assert response.json()["page_number"] == 3
    assert [page["page_number"] for page in payload["pages"]] == [1, 2, 3, 4]
    assert [page["title"] for page in payload["pages"]] == ["封面", "经营亮点", "经营亮点", "下一步计划"]
    assert payload["outline"]["total_pages"] == 4
    assert (local_settings.preview_slides_dir_path / "page-3.vue").read_text(encoding="utf-8") == VALID_SFC


def test_reorder_pages_endpoint_updates_page_numbers_outline_and_preview_files(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    asyncio.run(seed_all_generated_pages(session_factory=session_factory, settings=local_settings, project_id=project_id))
    app = build_test_app(settings=local_settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.put(f"/api/projects/{project_id}/pages/reorder", json={"page_numbers": [3, 1, 2]})
        project_response = client.get(f"/api/projects/{project_id}")

    payload = project_response.json()

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert [page["page_number"] for page in payload["pages"]] == [1, 2, 3]
    assert [page["title"] for page in payload["pages"]] == ["下一步计划", "封面", "经营亮点"]
    assert [page["title"] for page in payload["outline"]["pages"]] == ["下一步计划", "封面", "经营亮点"]
    assert (local_settings.preview_slides_dir_path / "page-1.vue").read_text(encoding="utf-8") == VALID_SFC.replace("经营亮点", "下一步计划")


def test_insert_page_after_endpoint_generates_new_page_and_reindexes(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    asyncio.run(seed_all_generated_pages(session_factory=session_factory, settings=local_settings, project_id=project_id))
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    generated_insert_code = VALID_SFC.replace("经营亮点", "新增增长机会")
    install_fake_runtime(monkeypatch, responses=[generated_insert_code], deliberation_enabled=False)

    with TestClient(app) as client:
        response = client.post(
            f"/api/projects/{project_id}/pages/2/insert-after",
            headers={"x-ppt-studio-api-key": "test-api-key"},
            json={"description": "新增一页说明 Q2 增长机会和行动抓手"},
        )
        project_response = client.get(f"/api/projects/{project_id}")

    payload = project_response.json()

    assert response.status_code == 200
    assert response.json()["page_number"] == 3
    assert response.json()["title"] == "新增一页说明 Q2 增长机会和行动抓手"
    assert [page["page_number"] for page in payload["pages"]] == [1, 2, 3, 4]
    assert payload["outline"]["total_pages"] == 4
    assert [page["page_number"] for page in payload["outline"]["pages"]] == [1, 2, 3, 4]
    assert payload["outline"]["pages"][2]["content_brief"] == "新增一页说明 Q2 增长机会和行动抓手"
    assert (local_settings.preview_slides_dir_path / "page-3.vue").read_text(encoding="utf-8") == generated_insert_code


def test_generate_single_page_streams_events_persists_code_and_writes_preview(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    install_fake_runtime(monkeypatch, responses=[VALID_SFC], deliberation_enabled=False)

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/projects/{project_id}/pages/2/generate",
            headers={"x-ppt-studio-api-key": "test-api-key"},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)
    event_names = [event["event"] for event in events]
    persisted_page = asyncio.run(load_generated_page(session_factory=session_factory, project_id=project_id, page_number=2))
    preview_file = Path(local_settings.preview_slides_dir_path / "page-2.vue").resolve()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "page_generating" in event_names
    assert "page_complete" in event_names
    assert event_names[-1] == "done"
    assert persisted_page is not None
    assert persisted_page.title == "经营亮点"
    assert persisted_page.vue_code == VALID_SFC
    assert preview_file.read_text(encoding="utf-8") == VALID_SFC


def test_regenerate_single_page_route_keeps_generate_behavior(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    install_fake_runtime(monkeypatch, responses=[VALID_SFC], deliberation_enabled=False)

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/projects/{project_id}/pages/2/regenerate",
            headers={"x-ppt-studio-api-key": "test-api-key"},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)
    event_names = [event["event"] for event in events]

    assert response.status_code == 200
    assert "page_generating" in event_names
    assert "page_complete" in event_names
    assert event_names[-1] == "done"


def test_generate_single_page_streams_error_for_invalid_page_number(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=True,
        )
    )
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    install_fake_runtime(monkeypatch, responses=[VALID_SFC], deliberation_enabled=False)

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/projects/{project_id}/pages/9/generate",
            headers={"x-ppt-studio-api-key": "test-api-key"},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)

    assert response.status_code == 200
    assert events[0]["event"] == "error"
    assert "当前有效范围为 1 到 3" in events[0]["data"]["message"]
    assert events[-1]["event"] == "done"


def test_generate_single_page_streams_error_when_outline_missing(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        create_project_with_outline_and_file(
            settings=local_settings,
            session_factory=session_factory,
            with_outline=False,
        )
    )
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    install_fake_runtime(monkeypatch, responses=[VALID_SFC], deliberation_enabled=False)

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/projects/{project_id}/pages/1/generate",
            headers={"x-ppt-studio-api-key": "test-api-key"},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)

    assert response.status_code == 200
    assert events[0]["event"] == "error"
    assert events[0]["data"]["message"] == "当前项目还没有可用大纲，请先完成大纲规划。"
    assert events[-1]["event"] == "done"


def parse_sse_events(raw_payload: str) -> list[dict[str, Any]]:
    normalized_payload = raw_payload.replace("\r\n", "\n")
    events: list[dict[str, Any]] = []

    for block in normalized_payload.split("\n\n"):
        stripped_block = block.strip()
        if not stripped_block:
            continue

        event_name = "message"
        data_lines: list[str] = []

        for line in stripped_block.split("\n"):
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())

        payload_text = "\n".join(data_lines)
        data = json.loads(payload_text) if payload_text else {}
        events.append({"event": event_name, "data": data})

    return events


def build_test_app(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    thumbnail_service: ThumbnailService | None = None,
) -> FastAPI:
    AppStatus.should_exit = False
    AppStatus.should_exit_event = None

    app = FastAPI()
    app.state.sse_manager = SSEManager()
    app.state.thumbnail_service = thumbnail_service or NoopThumbnailService(settings=settings)
    register_exception_handlers(app)
    app.include_router(projects_router)
    app.include_router(pages_router)

    async def override_db_session() -> Any:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings
    return app


class NoopThumbnailService(ThumbnailService):
    def schedule_refresh_from_preview(self, **_: Any) -> None:
        return None

    async def refresh_from_preview(self, **_: Any) -> list[Path]:
        return []


def install_fake_runtime(
    monkeypatch: pytest.MonkeyPatch,
    *,
    responses: list[Any],
    deliberation_enabled: bool,
) -> FakeChatModel:
    fake_model = FakeChatModel(responses)
    fake_runtime = LLMRuntime(
        config=LLMRuntimeConfig(
            provider=LLMProvider.OPENAI,
            model_name="fake-model",
            api_base_url="https://example.com/v1",
            api_key="test-api-key",
            deliberation_enabled=deliberation_enabled,
        ),
        settings=SettingsResponse(
            llm_provider=LLMProvider.OPENAI,
            model_name="fake-model",
            api_base_url="https://example.com/v1",
            multi_agent_deliberation_enabled=deliberation_enabled,
            default_theme=AppTheme.WARM_PAPER,
            storage_path="E:/tmp/projects",
        ),
        chat_model=fake_model,
    )

    async def fake_build_llm_runtime(*, settings_service: Any, api_key: str) -> LLMRuntime:
        assert settings_service is not None
        assert api_key == "test-api-key"
        return fake_runtime

    monkeypatch.setattr(pages_api, "build_llm_runtime", fake_build_llm_runtime)
    return fake_model


def build_local_settings(settings: Settings) -> Settings:
    preview_root = settings.backend_dir / "preview-server"
    return settings.model_copy(
        update={
            "preview_server_dir": preview_root,
            "preview_slides_dir": preview_root / "src" / "slides",
        }
    )


async def create_project_with_outline_and_file(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    with_outline: bool,
) -> str:
    async with session_factory() as session:
        project_service = ProjectService(session=session, settings=settings)
        theme_service = ThemeService(settings=settings)
        project = await project_service.create_project(ProjectCreate(name="Page API Test Project"))
        await project_service.save_theme_config(project.id, theme_service.resolve_theme(None))

        if with_outline:
            outline = OutlineSchema(
                title="Q1 经营汇报",
                total_pages=3,
                theme_suggestion="warm-orange",
                pages=[
                    OutlinePageSchema(
                        page_number=1,
                        title="封面",
                        type="cover",
                        content_brief="封面",
                        layout="center-hero",
                        data_refs=[],
                    ),
                    OutlinePageSchema(
                        page_number=2,
                        title="经营亮点",
                        type="keypoints",
                        content_brief="经营亮点页",
                        layout="bullet-grid",
                        data_refs=["metrics.csv"],
                    ),
                    OutlinePageSchema(
                        page_number=3,
                        title="下一步计划",
                        type="content",
                        content_brief="下一步计划页",
                        layout="title-body",
                        data_refs=[],
                    ),
                ],
            )
            await project_service.save_outline(project.id, outline)

        session.add(
            UploadedFile(
                project_id=project.id,
                original_name="metrics.csv",
                file_type="csv",
                file_path="uploads/metrics.csv",
                file_size=128,
                parse_status=FileParseStatus.PARSED,
                parsed_content={
                    "summary": "营收和利润率的关键数据已经整理。",
                    "key_points": ["营收增长 12%", "利润率提升 3pt"],
                    "structured_data": {"columns": ["month", "revenue", "margin"]},
                    "text_content": "Jan 12.1 18%, Feb 12.8 19%",
                },
            )
        )
        await session.commit()
        return project.id


async def load_generated_page(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    project_id: str,
    page_number: int,
) -> ProjectPage | None:
    async with session_factory() as session:
        return (
            await session.execute(
                select(ProjectPage).where(ProjectPage.project_id == project_id, ProjectPage.page_number == page_number)
            )
        ).scalar_one_or_none()


async def seed_generated_page(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    project_id: str,
    page_number: int,
    title: str,
) -> ProjectPage:
    async with session_factory() as session:
        page = ProjectPage(
            project_id=project_id,
            page_number=page_number,
            title=title,
            page_type="content",
            vue_code=VALID_SFC,
            status=PageStatus.GENERATED,
            version=1,
        )
        session.add(page)
        await session.commit()
        await session.refresh(page)
        session.add(
            PageVersion(
                page_id=page.id,
                version=1,
                vue_code=VALID_SFC,
                change_description="Generated by page generator.",
            )
        )
        await session.commit()
        await session.refresh(page)
        return page


async def optimize_seed_page(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    project_id: str,
    page_number: int,
) -> None:
    from app.services import PageService

    async with session_factory() as session:
        page_service = PageService(session=session, settings=settings)
        await page_service.optimize_existing_page(
            project_id=project_id,
            page_number=page_number,
            vue_code=VALID_SFC.replace("经营亮点", "经营亮点（优化）"),
            change_description="标题改为红色",
        )
        page_service.write_preview_slide(
            page_number=page_number,
            vue_code=VALID_SFC.replace("经营亮点", "经营亮点（优化）"),
        )


async def seed_all_generated_pages(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    project_id: str,
) -> None:
    async with session_factory() as session:
        page_service = pages_api.PageService(session=session, settings=settings)
        pages = [
            (1, "封面", VALID_SFC.replace("经营亮点", "封面")),
            (2, "经营亮点", VALID_SFC),
            (3, "下一步计划", VALID_SFC.replace("经营亮点", "下一步计划")),
        ]
        for page_number, title, vue_code in pages:
            await page_service.upsert_generated_page(
                project_id=project_id,
                page_number=page_number,
                title=title,
                page_type="content",
                vue_code=vue_code,
            )
            page_service.write_preview_slide(page_number=page_number, vue_code=vue_code)


async def load_page_versions(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    project_id: str,
    page_number: int,
) -> list[PageVersion]:
    async with session_factory() as session:
        page = (
            await session.execute(
                select(ProjectPage).where(ProjectPage.project_id == project_id, ProjectPage.page_number == page_number)
            )
        ).scalar_one()
        stmt = select(PageVersion).where(PageVersion.page_id == page.id).order_by(PageVersion.version.asc())
        return list((await session.execute(stmt)).scalars().all())
