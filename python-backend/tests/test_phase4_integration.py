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

import app.api.agent as agent_api
import app.api.pages as pages_api
from app.agents.llm import LLMRuntime, LLMRuntimeConfig
from app.api.agent import router as agent_router
from app.api.chat import router as chat_router
from app.api.pages import router as pages_router
from app.api.projects import router as projects_router
from app.config import Settings, get_settings
from app.db import get_db_session
from app.models import ChatMessage, PageVersion, ProjectPage
from app.models.enums import PageStatus
from app.schemas import AppTheme, LLMProvider, OutlinePageSchema, OutlineSchema, ProjectCreate, SettingsResponse
from app.services import ChatService, PageService, ProjectService, SSEManager, ThemeService


def build_sfc(marker: str) -> str:
    return f"""
<script setup lang="ts">
const highlights = ['营收增长', '续约提效', '{marker}']
</script>

<template>
  <main class="slide-page">
    <section class="hero">
      <h1 class="page-title">经营亮点</h1>
      <ul>
        <li v-for="item in highlights" :key="item">{{{{ item }}}}</li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.slide-page {{
  width: 1920px;
  height: 1080px;
  overflow: hidden;
  background: var(--slide-bg);
  color: var(--slide-text);
}}

.page-title {{
  color: var(--slide-danger);
}}
</style>
""".strip()


INITIAL_SFC = build_sfc("初始版本")
OPTIMIZED_ROUND_1_SFC = build_sfc("标题改红")
OPTIMIZED_ROUND_2_SFC = build_sfc("布局收紧")
OPTIMIZED_ROUND_3_SFC = build_sfc("淡入动效")
PAGE_2_SFC = build_sfc("第二页")


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


def test_phase4_preview_optimization_runs_three_rounds_and_keeps_histories_consistent(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        seed_phase4_project(
            settings=local_settings,
            session_factory=session_factory,
            include_project_history=True,
        )
    )
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    fake_model = install_fake_runtime(
        monkeypatch,
        responses=[
            OPTIMIZED_ROUND_1_SFC,
            "标题改为红色",
            OPTIMIZED_ROUND_2_SFC,
            "布局更紧凑",
            OPTIMIZED_ROUND_3_SFC,
            "加入淡入动效",
        ],
        deliberation_enabled=False,
    )
    instructions = [
        "把标题改成红色",
        "把卡片布局再收紧一点",
        "给主要内容加淡入动效",
    ]

    with TestClient(app) as client:
        for expected_version, instruction in enumerate(instructions, start=2):
            with client.stream(
                "POST",
                f"/api/projects/{project_id}/agent/chat",
                headers={"x-ppt-studio-api-key": "test-api-key"},
                json={"message": instruction, "page_number": 1},
            ) as response:
                payload = "".join(response.iter_text())

            events = parse_sse_events(payload)
            updated_event = next(event for event in events if event["event"] == "page_updated")

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert [event["event"] for event in events][-1] == "done"
            assert updated_event["data"]["page_number"] == 1
            assert updated_event["data"]["version"] == expected_version

        project_response = client.get(f"/api/projects/{project_id}")
        page_1_history_response = client.get(f"/api/projects/{project_id}/chat/messages?page_number=1")
        page_2_history_response = client.get(f"/api/projects/{project_id}/chat/messages?page_number=2")
        project_history_response = client.get(f"/api/projects/{project_id}/chat/messages")
        project_with_page_history_response = client.get(
            f"/api/projects/{project_id}/chat/messages?include_page_messages=true"
        )

    page = asyncio.run(load_page(session_factory=session_factory, project_id=project_id, page_number=1))
    versions = asyncio.run(load_page_versions(session_factory=session_factory, project_id=project_id, page_number=1))
    preview_file = Path(local_settings.preview_slides_dir_path / "page-1.vue").resolve()

    assert len(fake_model.calls) == 6
    assert page is not None
    assert page.version == 4
    assert page.vue_code == OPTIMIZED_ROUND_3_SFC
    assert [version.version for version in versions] == [1, 2, 3, 4]
    assert [version.change_description for version in versions[1:]] == [
        "标题改为红色",
        "布局更紧凑",
        "加入淡入动效",
    ]
    assert preview_file.read_text(encoding="utf-8") == OPTIMIZED_ROUND_3_SFC

    project_payload = project_response.json()
    page_1_payload = page_1_history_response.json()
    page_2_payload = page_2_history_response.json()
    project_history_payload = project_history_response.json()
    project_with_page_history_payload = project_with_page_history_response.json()
    page_1_detail = next(page for page in project_payload["pages"] if page["page_number"] == 1)
    page_2_detail = next(page for page in project_payload["pages"] if page["page_number"] == 2)

    assert project_response.status_code == 200
    assert page_1_detail["version"] == 4
    assert page_1_detail["chat_message_count"] == 6
    assert page_2_detail["chat_message_count"] == 0
    assert page_1_history_response.status_code == 200
    assert page_1_payload["total"] == 6
    assert [message["content"] for message in page_1_payload["messages"] if message["role"] == "user"] == instructions
    assert [message["content"] for message in page_1_payload["messages"] if message["role"] == "assistant"] == [
        "已修改第 1 页：标题改为红色",
        "已修改第 1 页：布局更紧凑",
        "已修改第 1 页：加入淡入动效",
    ]
    assert page_2_history_response.status_code == 200
    assert page_2_payload["total"] == 0
    assert project_history_response.status_code == 200
    assert project_history_payload["total"] == 2
    assert all(message["page_number"] is None for message in project_history_payload["messages"])
    assert project_with_page_history_response.status_code == 200
    assert project_with_page_history_payload["total"] == 8
    assert any(
        message["page_number"] == 1 and message["content"] == "已修改第 1 页：加入淡入动效"
        for message in project_with_page_history_payload["messages"]
    )


def test_phase4_page_optimizer_deliberation_fallback_streams_and_persists_draft(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(
        seed_phase4_project(
            settings=local_settings,
            session_factory=session_factory,
            include_project_history=False,
        )
    )
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    install_fake_runtime(
        monkeypatch,
        responses=[
            OPTIMIZED_ROUND_1_SFC,
            RuntimeError("critic failed"),
            "思辨失败后采用草案",
        ],
        deliberation_enabled=True,
    )

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/projects/{project_id}/agent/chat",
            headers={"x-ppt-studio-api-key": "test-api-key"},
            json={"message": "把标题改成红色，并保持其它内容不变", "page_number": 1},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)
    event_names = [event["event"] for event in events]
    fallback_summary = next(event for event in events if event["event"] == "deliberation_summary")
    updated_event = next(event for event in events if event["event"] == "page_updated")
    page = asyncio.run(load_page(session_factory=session_factory, project_id=project_id, page_number=1))
    versions = asyncio.run(load_page_versions(session_factory=session_factory, project_id=project_id, page_number=1))
    messages = asyncio.run(load_messages(session_factory=session_factory, project_id=project_id))
    preview_file = Path(local_settings.preview_slides_dir_path / "page-1.vue").resolve()

    assert response.status_code == 200
    assert "deliberation_started" in event_names
    assert event_names.count("deliberation_round") == 1
    assert "deliberation_summary" in event_names
    assert "page_updated" in event_names
    assert event_names[-1] == "done"
    assert "回退到 Draft 优化结果" in fallback_summary["data"]["summary"]
    assert updated_event["data"]["change_description"] == "思辨失败后采用草案"
    assert updated_event["data"]["vue_code"] == OPTIMIZED_ROUND_1_SFC
    assert page is not None
    assert page.version == 2
    assert page.vue_code == OPTIMIZED_ROUND_1_SFC
    assert [version.version for version in versions] == [1, 2]
    assert versions[-1].change_description == "思辨失败后采用草案"
    assert preview_file.read_text(encoding="utf-8") == OPTIMIZED_ROUND_1_SFC
    assert messages[-1].page_number == 1
    assert messages[-1].content == "已修改第 1 页：思辨失败后采用草案"


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
    app.include_router(chat_router)
    app.include_router(pages_router)
    app.include_router(agent_router)

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

    monkeypatch.setattr(agent_api, "build_llm_runtime", fake_build_llm_runtime)
    monkeypatch.setattr(pages_api, "build_llm_runtime", fake_build_llm_runtime)
    return fake_model


def build_local_settings(settings: Settings) -> Settings:
    preview_root = settings.backend_dir / "preview-server"
    local_settings = settings.model_copy(
        update={
            "preview_server_dir": preview_root,
            "preview_slides_dir": preview_root / "src" / "slides",
        }
    )
    local_settings.ensure_directories()
    return local_settings


async def seed_phase4_project(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    include_project_history: bool,
) -> str:
    async with session_factory() as session:
        project_service = ProjectService(session=session, settings=settings)
        theme_service = ThemeService(settings=settings)
        project = await project_service.create_project(ProjectCreate(name="Phase 4 Integration Project"))
        await project_service.save_theme_config(project.id, theme_service.resolve_theme(None))
        await project_service.save_outline(
            project.id,
            OutlineSchema(
                title="Q1 经营汇报",
                total_pages=2,
                theme_suggestion="warm-paper",
                pages=[
                    OutlinePageSchema(
                        page_number=1,
                        title="经营亮点",
                        type="data",
                        content_brief="展示经营亮点",
                        layout="hero-card",
                        data_refs=[],
                    ),
                    OutlinePageSchema(
                        page_number=2,
                        title="风险提示",
                        type="content",
                        content_brief="展示关键风险",
                        layout="title-body",
                        data_refs=[],
                    ),
                ],
            ),
        )

        page_service = PageService(session=session, settings=settings)
        page_1 = await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=1,
            title="经营亮点",
            page_type="data",
            vue_code=INITIAL_SFC,
            status=PageStatus.GENERATED,
        )
        page_2 = await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=2,
            title="风险提示",
            page_type="content",
            vue_code=PAGE_2_SFC,
            status=PageStatus.GENERATED,
        )
        page_service.write_preview_slide(page_number=page_1.page_number, vue_code=INITIAL_SFC)
        page_service.write_preview_slide(page_number=page_2.page_number, vue_code=PAGE_2_SFC)

        if include_project_history:
            chat_service = ChatService(session=session)
            await chat_service.create_message(
                project_id=project.id,
                role="user",
                content="请先规划项目级大纲",
                message_type="text",
            )
            await chat_service.create_message(
                project_id=project.id,
                role="assistant",
                content="已生成《Q1 经营汇报》共 2 页大纲。",
                message_type="outline",
                metadata={
                    "outline": {
                        "title": "Q1 经营汇报",
                        "total_pages": 2,
                        "theme_suggestion": "warm-paper",
                        "pages": [{"title": "经营亮点"}, {"title": "风险提示"}],
                    }
                },
            )

        return project.id


async def load_page(
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


async def load_messages(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    project_id: str,
) -> list[ChatMessage]:
    async with session_factory() as session:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        return list((await session.execute(stmt)).scalars().all())
