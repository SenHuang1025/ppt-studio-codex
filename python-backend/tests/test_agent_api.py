from __future__ import annotations

import asyncio
import io
import json
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sse_starlette.sse import AppStatus

import app.api.agent as agent_api
from app.agents.llm import LLMRuntime, LLMRuntimeConfig
from app.api.agent import router as agent_router
from app.api.projects import router as projects_router
from app.config import Settings, get_settings
from app.db import get_db_session
from app.models import ChatMessage
from app.schemas import AppTheme, LLMProvider, ProjectCreate, SettingsResponse
from app.services import FileService, ProjectService, SSEManager

FILE_ANALYZER_RESPONSE = '{"summary":"材料聚焦营收增长与下一步策略。","key_points":["营收增长","重点客户续约","下一季度计划"]}'
DIRECT_REPLY_RESPONSE = "你好，我现在可以先帮你分析资料并规划 PPT 大纲。"
OUTLINE_RESPONSE = """
{
  "title": "Q1 经营汇报",
  "total_pages": 3,
  "theme_suggestion": "warm-paper",
  "pages": [
    {
      "page_number": 1,
      "title": "Q1 经营汇报",
      "type": "cover",
      "content_brief": "季度经营汇报封面",
      "layout": "center-hero",
      "data_refs": []
    },
    {
      "page_number": 2,
      "title": "经营亮点",
      "type": "keypoints",
      "content_brief": "概览本季度的关键亮点",
      "layout": "bullet-grid",
      "data_refs": ["brief.txt"]
    },
    {
      "page_number": 3,
      "title": "下一步计划",
      "type": "content",
      "content_brief": "接下来一季度的工作安排",
      "layout": "title-body",
      "data_refs": []
    }
  ]
}
""".strip()
SYNTHESIS_RESPONSE = """
{
  "title": "Q1 经营汇报（优化版）",
  "total_pages": 4,
  "theme_suggestion": "warm-paper",
  "pages": [
    {
      "page_number": 1,
      "title": "Q1 经营汇报",
      "type": "cover",
      "content_brief": "季度经营汇报封面",
      "layout": "center-hero",
      "data_refs": []
    },
    {
      "page_number": 2,
      "title": "整体提纲",
      "type": "toc",
      "content_brief": "本次汇报的四个板块",
      "layout": "section-list",
      "data_refs": []
    },
    {
      "page_number": 3,
      "title": "经营亮点",
      "type": "keypoints",
      "content_brief": "概览本季度的关键亮点",
      "layout": "bullet-grid",
      "data_refs": ["brief.txt"]
    },
    {
      "page_number": 4,
      "title": "下一步计划",
      "type": "content",
      "content_brief": "接下来一季度的工作安排",
      "layout": "title-body",
      "data_refs": []
    }
  ]
}
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


def test_agent_chat_returns_400_when_api_key_is_missing(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app = build_test_app(settings=settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.post(
            "/api/projects/project-1/agent/chat",
            json={"message": "请开始规划"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "请先在设置页配置 API Key。"


def test_agent_chat_streams_file_analysis_outline_and_done(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = asyncio.run(create_project(settings=settings, session_factory=session_factory, with_file=True))
    app = build_test_app(settings=settings, session_factory=session_factory)
    install_fake_runtime(
        monkeypatch,
        responses=[FILE_ANALYZER_RESPONSE, OUTLINE_RESPONSE],
        deliberation_enabled=False,
    )

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/projects/{project_id}/agent/chat",
            headers={"x-ppt-studio-api-key": "test-api-key"},
            json={"message": "请根据资料生成季度经营汇报 PPT 大纲"},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)
    event_names = [event["event"] for event in events]

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert event_names[0] == "thinking"
    assert "file_parsed" in event_names
    assert "outline" in event_names
    assert event_names[-1] == "done"


def test_agent_chat_streams_assistant_message_for_general_chat(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = asyncio.run(create_project(settings=settings, session_factory=session_factory, with_file=False))
    app = build_test_app(settings=settings, session_factory=session_factory)
    install_fake_runtime(
        monkeypatch,
        responses=[DIRECT_REPLY_RESPONSE],
        deliberation_enabled=False,
    )

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/projects/{project_id}/agent/chat",
            headers={"x-ppt-studio-api-key": "test-api-key"},
            json={"message": "你好"},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)

    assert response.status_code == 200
    assert [event["event"] for event in events][-1] == "done"
    assert any(event["event"] == "assistant_message" for event in events)


def test_agent_chat_streams_deliberation_events_when_enabled(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = asyncio.run(create_project(settings=settings, session_factory=session_factory, with_file=False))
    app = build_test_app(settings=settings, session_factory=session_factory)
    install_fake_runtime(
        monkeypatch,
        responses=[OUTLINE_RESPONSE, "建议补一页整体提纲，强化叙事节奏。", SYNTHESIS_RESPONSE],
        deliberation_enabled=True,
    )

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/projects/{project_id}/agent/chat",
            headers={"x-ppt-studio-api-key": "test-api-key"},
            json={"message": "帮我规划一份季度经营汇报 PPT"},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)
    event_names = [event["event"] for event in events]

    assert response.status_code == 200
    assert "deliberation_started" in event_names
    assert "deliberation_round" in event_names
    assert "deliberation_summary" in event_names
    assert "outline" in event_names
    assert event_names[-1] == "done"


def test_agent_chat_persists_outline_to_project(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = asyncio.run(create_project(settings=settings, session_factory=session_factory, with_file=False))
    app = build_test_app(settings=settings, session_factory=session_factory)
    install_fake_runtime(
        monkeypatch,
        responses=[OUTLINE_RESPONSE],
        deliberation_enabled=False,
    )

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/projects/{project_id}/agent/chat",
            headers={"x-ppt-studio-api-key": "test-api-key"},
            json={"message": "帮我规划一份季度经营汇报 PPT"},
        ) as response:
            payload = "".join(response.iter_text())

        project_response = client.get(f"/api/projects/{project_id}")

    events = parse_sse_events(payload)
    project_payload = project_response.json()

    assert response.status_code == 200
    assert any(event["event"] == "outline" for event in events)
    assert project_response.status_code == 200
    assert project_payload["status"] == "planning"
    assert project_payload["total_pages"] == 3
    assert project_payload["outline"]["title"] == "Q1 经营汇报"


def test_agent_chat_persists_user_and_outline_messages(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = asyncio.run(create_project(settings=settings, session_factory=session_factory, with_file=False))
    app = build_test_app(settings=settings, session_factory=session_factory)
    install_fake_runtime(
        monkeypatch,
        responses=[OUTLINE_RESPONSE],
        deliberation_enabled=False,
    )

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/projects/{project_id}/agent/chat",
            headers={"x-ppt-studio-api-key": "test-api-key"},
            json={"message": "帮我规划一份季度经营汇报 PPT"},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)
    messages = asyncio.run(load_chat_messages(session_factory=session_factory, project_id=project_id))

    assert response.status_code == 200
    assert any(event["event"] == "outline" for event in events)
    assert len(messages) == 2
    assert messages[0].role.value == "user"
    assert messages[0].message_type.value == "text"
    assert messages[0].content == "帮我规划一份季度经营汇报 PPT"
    assert messages[1].role.value == "assistant"
    assert messages[1].message_type.value == "outline"
    assert messages[1].content == "已生成《Q1 经营汇报》共 3 页大纲。"
    assert messages[1].metadata_json is not None
    assert messages[1].metadata_json["outline"]["title"] == "Q1 经营汇报"
    assert messages[1].metadata_json["outline"]["total_pages"] == 3


def test_agent_chat_reuses_persisted_history_on_second_request(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = asyncio.run(create_project(settings=settings, session_factory=session_factory, with_file=False))
    app = build_test_app(settings=settings, session_factory=session_factory)
    fake_model = install_fake_runtime(
        monkeypatch,
        responses=[OUTLINE_RESPONSE, OUTLINE_RESPONSE],
        deliberation_enabled=False,
    )

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/projects/{project_id}/agent/chat",
            headers={"x-ppt-studio-api-key": "test-api-key"},
            json={"message": "帮我规划一份季度经营汇报 PPT"},
        ) as response:
            _ = "".join(response.iter_text())

        with client.stream(
            "POST",
            f"/api/projects/{project_id}/agent/chat",
            headers={"x-ppt-studio-api-key": "test-api-key"},
            json={"message": "在现有基础上新增一页风险提示"},
        ) as response:
            _ = "".join(response.iter_text())

    assert len(fake_model.calls) == 2
    second_request_prompt = fake_model.calls[1][1][1]
    assert "帮我规划一份季度经营汇报 PPT" in second_request_prompt
    assert "已生成《Q1 经营汇报》共 3 页大纲。" in second_request_prompt
    assert "在现有基础上新增一页风险提示" in second_request_prompt


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
    return fake_model


async def create_project(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    with_file: bool,
) -> str:
    async with session_factory() as session:
        project_service = ProjectService(session=session, settings=settings)
        project = await project_service.create_project(ProjectCreate(name="Agent Test Project"))

        if with_file:
            file_service = FileService(session=session, settings=settings)
            upload_file = UploadFile(filename="brief.txt", file=io.BytesIO("营收增长，下一步计划。".encode("utf-8")))
            await file_service.upload_file(project.id, upload_file)

        return project.id


async def load_chat_messages(
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
