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
from app.models import ProjectPage, UploadedFile
from app.models.enums import FileParseStatus
from app.schemas import (
    AppTheme,
    LLMProvider,
    OutlinePageSchema,
    OutlineSchema,
    ProjectCreate,
    SettingsResponse,
)
from app.services import ProjectService, SSEManager, ThemeService

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
    assert response.json()["detail"] == "请先在设置页配置 API Key。"


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


def build_test_app(*, settings: Settings, session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    AppStatus.should_exit = False
    AppStatus.should_exit_event = None

    app = FastAPI()
    app.state.sse_manager = SSEManager()
    app.include_router(projects_router)
    app.include_router(pages_router)

    async def override_db_session() -> Any:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings
    return app


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
