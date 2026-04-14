from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sse_starlette.sse import AppStatus

import app.agents.llm as llm_module
from app.api.router import router as api_router
from app.config import Settings, get_settings
from app.db import get_db_session
from app.services import SSEManager
from tests.sample_files import write_docx_file, write_excel_file, write_pdf_file

FILE_ANALYZER_RESPONSE = """
{
  "summary": "材料显示季度营收持续增长，适合组织为经营汇报。",
  "key_points": ["营收增长", "成本受控", "需要给出下季度计划"]
}
""".strip()

SECOND_FILE_ANALYZER_RESPONSE = """
{
  "summary": "文档补充了经营回顾、执行动作和风险背景。",
  "key_points": ["经营回顾", "执行动作", "风险背景"]
}
""".strip()

INITIAL_OUTLINE_RESPONSE = """
{
  "title": "季度经营汇报",
  "total_pages": 4,
  "theme_suggestion": "warm-paper",
  "pages": [
    {
      "page_number": 1,
      "title": "季度经营汇报",
      "type": "cover",
      "content_brief": "季度经营汇报封面",
      "layout": "center-hero",
      "data_refs": []
    },
    {
      "page_number": 2,
      "title": "核心结论",
      "type": "keypoints",
      "content_brief": "提炼季度的三项核心经营结论",
      "layout": "bullet-grid",
      "data_refs": ["sales.xlsx"]
    },
    {
      "page_number": 3,
      "title": "销售表现",
      "type": "data",
      "content_brief": "展示季度销售额、成本和趋势变化",
      "layout": "kpi-grid",
      "data_refs": ["sales.xlsx"]
    },
    {
      "page_number": 4,
      "title": "下一步计划",
      "type": "content",
      "content_brief": "给出下一季度的关键行动安排",
      "layout": "title-body",
      "data_refs": []
    }
  ]
}
""".strip()

COMBINED_OUTLINE_RESPONSE = """
{
  "title": "综合资料经营汇报",
  "total_pages": 4,
  "theme_suggestion": "warm-paper",
  "pages": [
    {
      "page_number": 1,
      "title": "综合资料经营汇报",
      "type": "cover",
      "content_brief": "基于多份资料的经营汇报封面",
      "layout": "center-hero",
      "data_refs": []
    },
    {
      "page_number": 2,
      "title": "资料综述",
      "type": "toc",
      "content_brief": "交代本次汇报的资料来源和板块结构",
      "layout": "section-list",
      "data_refs": ["brief.docx", "report.pdf"]
    },
    {
      "page_number": 3,
      "title": "经营回顾",
      "type": "content",
      "content_brief": "汇总 Word 与 PDF 中的关键经营信息",
      "layout": "title-body",
      "data_refs": ["brief.docx", "report.pdf"]
    },
    {
      "page_number": 4,
      "title": "建议动作",
      "type": "content",
      "content_brief": "给出后续行动建议和汇报收束",
      "layout": "title-body",
      "data_refs": ["brief.docx"]
    }
  ]
}
""".strip()

REVISED_OUTLINE_RESPONSE = """
{
  "title": "季度经营汇报",
  "total_pages": 5,
  "theme_suggestion": "warm-paper",
  "pages": [
    {
      "page_number": 1,
      "title": "季度经营汇报",
      "type": "cover",
      "content_brief": "季度经营汇报封面",
      "layout": "center-hero",
      "data_refs": []
    },
    {
      "page_number": 2,
      "title": "总结先行",
      "type": "keypoints",
      "content_brief": "把结论前置，先给出整体判断",
      "layout": "bullet-grid",
      "data_refs": ["sales.xlsx"]
    },
    {
      "page_number": 3,
      "title": "销售表现",
      "type": "data",
      "content_brief": "展示季度销售额、成本和趋势变化",
      "layout": "kpi-grid",
      "data_refs": ["sales.xlsx"]
    },
    {
      "page_number": 4,
      "title": "风险提示",
      "type": "content",
      "content_brief": "新增风险识别与应对建议",
      "layout": "title-body",
      "data_refs": []
    },
    {
      "page_number": 5,
      "title": "下一步计划",
      "type": "content",
      "content_brief": "给出下一季度的关键行动安排",
      "layout": "title-body",
      "data_refs": []
    }
  ]
}
""".strip()

DELIBERATION_DRAFT_RESPONSE = """
{
  "title": "经营复盘与规划",
  "total_pages": 4,
  "theme_suggestion": "warm-paper",
  "pages": [
    {
      "page_number": 1,
      "title": "经营复盘与规划",
      "type": "cover",
      "content_brief": "经营复盘与规划封面",
      "layout": "center-hero",
      "data_refs": []
    },
    {
      "page_number": 2,
      "title": "核心结论",
      "type": "keypoints",
      "content_brief": "概览核心经营判断",
      "layout": "bullet-grid",
      "data_refs": []
    },
    {
      "page_number": 3,
      "title": "经营回顾",
      "type": "content",
      "content_brief": "复盘本季度执行情况",
      "layout": "title-body",
      "data_refs": []
    },
    {
      "page_number": 4,
      "title": "下一步计划",
      "type": "content",
      "content_brief": "列出关键行动项",
      "layout": "title-body",
      "data_refs": []
    }
  ]
}
""".strip()

DELIBERATION_SYNTHESIS_RESPONSE = """
{
  "title": "经营复盘与规划（思辨版）",
  "total_pages": 5,
  "theme_suggestion": "warm-paper",
  "pages": [
    {
      "page_number": 1,
      "title": "经营复盘与规划",
      "type": "cover",
      "content_brief": "经营复盘与规划封面",
      "layout": "center-hero",
      "data_refs": []
    },
    {
      "page_number": 2,
      "title": "执行摘要",
      "type": "keypoints",
      "content_brief": "先给出整体结论和关键建议",
      "layout": "bullet-grid",
      "data_refs": []
    },
    {
      "page_number": 3,
      "title": "经营回顾",
      "type": "content",
      "content_brief": "复盘本季度执行情况",
      "layout": "title-body",
      "data_refs": []
    },
    {
      "page_number": 4,
      "title": "风险控制",
      "type": "content",
      "content_brief": "补充主要风险与控制动作",
      "layout": "title-body",
      "data_refs": []
    },
    {
      "page_number": 5,
      "title": "下一步计划",
      "type": "content",
      "content_brief": "列出关键行动项",
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
    def __init__(self, *, responses: list[Any], runtime_config: Any) -> None:
        self._responses = list(responses)
        self.calls: list[Any] = []
        self.runtime_config = runtime_config

    async def ainvoke(self, messages: Any) -> FakeModelResponse:
        self.calls.append(messages)
        if not self._responses:
            raise AssertionError("Fake model ran out of configured responses.")

        next_response = self._responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return FakeModelResponse(content=str(next_response))


class FakeChatModelFactory:
    def __init__(self, response_batches: list[list[Any]]) -> None:
        self._response_batches = [list(batch) for batch in response_batches]
        self.instances: list[FakeChatModel] = []
        self.runtime_configs: list[Any] = []

    def __call__(self, config: Any) -> FakeChatModel:
        if not self._response_batches:
            raise AssertionError("No fake model response batch is configured for the next runtime.")

        self.runtime_configs.append(config)
        model = FakeChatModel(
            responses=self._response_batches.pop(0),
            runtime_config=config,
        )
        self.instances.append(model)
        return model

    @property
    def remaining_batches(self) -> int:
        return len(self._response_batches)


def test_phase2_excel_end_to_end_flow(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = build_test_app(settings=settings, session_factory=session_factory)
    excel_path = write_excel_file(tmp_path / "sales.xlsx")
    factory = install_fake_chat_model_factory(
        monkeypatch,
        response_batches=[[FILE_ANALYZER_RESPONSE, INITIAL_OUTLINE_RESPONSE]],
    )

    with TestClient(app) as client:
        project = create_project(client, name="Excel Integration Project")
        upload_response = upload_file_via_api(client, project_id=project["id"], file_path=excel_path)
        status_code, headers, events = stream_agent_chat(
            client,
            project_id=project["id"],
            message="请根据这份销售数据生成季度经营汇报 PPT 大纲",
        )
        project_detail = get_project_detail(client, project["id"])
        file_list = list_project_files(client, project["id"])
        messages = list_chat_messages(client, project["id"])

    event_names = [event["event"] for event in events]

    assert upload_response["parse_status"] == "pending"
    assert status_code == 200
    assert headers["content-type"].startswith("text/event-stream")
    assert_event_order(event_names, ["thinking", "file_parsed", "outline", "done"])
    assert file_list["files"][0]["original_name"] == "sales.xlsx"
    assert file_list["files"][0]["parse_status"] == "parsed"
    assert project_detail["status"] == "planning"
    assert project_detail["outline"]["title"] == "季度经营汇报"
    assert project_detail["outline"]["total_pages"] == 4
    assert [page["title"] for page in project_detail["outline"]["pages"]] == [
        "季度经营汇报",
        "核心结论",
        "销售表现",
        "下一步计划",
    ]
    assert messages["total"] == 2
    assert messages["messages"][0]["role"] == "user"
    assert messages["messages"][0]["message_type"] == "text"
    assert messages["messages"][1]["role"] == "assistant"
    assert messages["messages"][1]["message_type"] == "outline"
    assert messages["messages"][1]["metadata"]["outline"]["title"] == "季度经营汇报"
    assert messages["messages"][1]["metadata"]["outline"]["total_pages"] == 4
    assert len(factory.instances) == 1
    assert len(factory.instances[0].calls) == 2
    assert factory.remaining_batches == 0


def test_phase2_word_and_pdf_multi_file_flow(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = build_test_app(settings=settings, session_factory=session_factory)
    docx_path = write_docx_file(tmp_path / "brief.docx")
    pdf_path = write_pdf_file(tmp_path / "report.pdf")
    factory = install_fake_chat_model_factory(
        monkeypatch,
        response_batches=[[FILE_ANALYZER_RESPONSE, SECOND_FILE_ANALYZER_RESPONSE, COMBINED_OUTLINE_RESPONSE]],
    )

    with TestClient(app) as client:
        project = create_project(client, name="Multi File Integration Project")
        upload_file_via_api(client, project_id=project["id"], file_path=docx_path)
        upload_file_via_api(client, project_id=project["id"], file_path=pdf_path)
        status_code, _, events = stream_agent_chat(
            client,
            project_id=project["id"],
            message="请综合这两份资料生成经营汇报大纲",
        )
        project_detail = get_project_detail(client, project["id"])
        file_list = list_project_files(client, project["id"])
        messages = list_chat_messages(client, project["id"])

    event_names = [event["event"] for event in events]
    parsed_file_events = [event for event in events if event["event"] == "file_parsed"]
    file_statuses = {item["original_name"]: item["parse_status"] for item in file_list["files"]}

    assert status_code == 200
    assert event_names.count("file_parsed") == 2
    assert_event_order(event_names, ["file_parsed", "file_parsed", "outline", "done"])
    assert {event["data"]["file_name"] for event in parsed_file_events} == {"brief.docx", "report.pdf"}
    assert project_detail["outline"]["title"] == "综合资料经营汇报"
    assert project_detail["outline"]["total_pages"] == 4
    assert file_statuses == {"brief.docx": "parsed", "report.pdf": "parsed"}
    assert messages["total"] == 2
    assert [message["role"] for message in messages["messages"]] == ["user", "assistant"]
    assert messages["messages"][1]["message_type"] == "outline"
    assert messages["messages"][1]["metadata"]["outline"]["title"] == "综合资料经营汇报"
    assert len(factory.instances) == 1
    assert len(factory.instances[0].calls) == 3


def test_phase2_multi_turn_outline_adjustment_preserves_context(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = build_test_app(settings=settings, session_factory=session_factory)
    excel_path = write_excel_file(tmp_path / "sales.xlsx")
    factory = install_fake_chat_model_factory(
        monkeypatch,
        response_batches=[
            [FILE_ANALYZER_RESPONSE, INITIAL_OUTLINE_RESPONSE],
            [REVISED_OUTLINE_RESPONSE],
        ],
    )

    with TestClient(app) as client:
        project = create_project(client, name="Multi Turn Integration Project")
        upload_file_via_api(client, project_id=project["id"], file_path=excel_path)
        first_status_code, _, first_events = stream_agent_chat(
            client,
            project_id=project["id"],
            message="请先根据销售数据生成季度经营汇报大纲",
        )
        second_status_code, _, second_events = stream_agent_chat(
            client,
            project_id=project["id"],
            message="在现有基础上新增一页风险提示，并把总结提前",
        )
        project_detail = get_project_detail(client, project["id"])
        messages = list_chat_messages(client, project["id"])

    second_prompt = factory.instances[1].calls[0][1][1]

    assert first_status_code == 200
    assert second_status_code == 200
    assert "file_parsed" not in [event["event"] for event in second_events]
    assert [event["event"] for event in second_events][-1] == "done"
    assert project_detail["outline"]["total_pages"] == 5
    assert [page["title"] for page in project_detail["outline"]["pages"]] == [
        "季度经营汇报",
        "总结先行",
        "销售表现",
        "风险提示",
        "下一步计划",
    ]
    assert messages["total"] == 4
    assert [message["role"] for message in messages["messages"]] == ["user", "assistant", "user", "assistant"]
    assert [message["message_type"] for message in messages["messages"]] == ["text", "outline", "text", "outline"]
    assert "请先根据销售数据生成季度经营汇报大纲" in second_prompt
    assert "已生成《季度经营汇报》共 4 页大纲。" in second_prompt
    assert "在现有基础上新增一页风险提示，并把总结提前" in second_prompt
    assert len(factory.instances) == 2
    assert [len(instance.calls) for instance in factory.instances] == [2, 1]
    assert [event["event"] for event in first_events].count("outline") == 1


def test_phase2_deliberation_setting_controls_runtime_and_sse(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = build_test_app(settings=settings, session_factory=session_factory)
    factory = install_fake_chat_model_factory(
        monkeypatch,
        response_batches=[
            [INITIAL_OUTLINE_RESPONSE],
            [
                DELIBERATION_DRAFT_RESPONSE,
                "建议增加执行摘要，并单独补一页风险控制。",
                DELIBERATION_SYNTHESIS_RESPONSE,
            ],
        ],
    )

    with TestClient(app) as client:
        project = create_project(client, name="Deliberation Integration Project")
        update_settings(client, {"multi_agent_deliberation_enabled": False})
        disabled_status_code, _, disabled_events = stream_agent_chat(
            client,
            project_id=project["id"],
            message="请规划一份经营分析 PPT",
        )
        update_settings(client, {"multi_agent_deliberation_enabled": True})
        enabled_status_code, _, enabled_events = stream_agent_chat(
            client,
            project_id=project["id"],
            message="请重新规划一份更完整的经营分析 PPT",
        )
        project_detail = get_project_detail(client, project["id"])

    disabled_event_names = [event["event"] for event in disabled_events]
    enabled_event_names = [event["event"] for event in enabled_events]

    assert disabled_status_code == 200
    assert enabled_status_code == 200
    assert "deliberation_started" not in disabled_event_names
    assert "deliberation_round" not in disabled_event_names
    assert "deliberation_summary" not in disabled_event_names
    assert "deliberation_started" in enabled_event_names
    assert "deliberation_round" in enabled_event_names
    assert "deliberation_summary" in enabled_event_names
    assert_event_order(enabled_event_names, ["deliberation_started", "deliberation_round", "deliberation_summary", "outline", "done"])
    assert project_detail["outline"]["title"] == "经营复盘与规划（思辨版）"
    assert project_detail["outline"]["total_pages"] == 5
    assert [config.deliberation_enabled for config in factory.runtime_configs] == [False, True]
    assert [len(instance.calls) for instance in factory.instances] == [1, 3]


def test_phase2_rejects_unsupported_file_upload(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app = build_test_app(settings=settings, session_factory=session_factory)

    with TestClient(app) as client:
        project = create_project(client, name="Invalid Upload Integration Project")
        response = client.post(
            f"/api/projects/{project['id']}/files",
            files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
        )

    assert response.status_code == 400
    assert "File type '.exe' is not supported." in response.json()["detail"]


def test_phase2_requires_api_key_for_agent_chat(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app = build_test_app(settings=settings, session_factory=session_factory)

    with TestClient(app) as client:
        project = create_project(client, name="Missing API Key Integration Project")
        response = client.post(
            f"/api/projects/{project['id']}/agent/chat",
            json={"message": "请帮我规划一份经营汇报大纲"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "请先在设置页配置 API Key。"


def test_phase2_surfaces_planner_failures_without_persisting_outline(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = build_test_app(settings=settings, session_factory=session_factory)
    factory = install_fake_chat_model_factory(
        monkeypatch,
        response_batches=[[RuntimeError("planner draft failed"), RuntimeError("planner repair failed")]],
    )

    with TestClient(app) as client:
        project = create_project(client, name="Planner Failure Integration Project")
        status_code, _, events = stream_agent_chat(
            client,
            project_id=project["id"],
            message="请规划一份经营汇报大纲",
        )
        project_detail = get_project_detail(client, project["id"])
        messages = list_chat_messages(client, project["id"])

    error_events = [event for event in events if event["event"] == "error"]

    assert status_code == 200
    assert error_events
    assert error_events[0]["data"]["message"].startswith("实时会话失败：")
    assert [event["event"] for event in events][-1] == "done"
    assert "outline" not in [event["event"] for event in events]
    assert project_detail["outline"] is None
    assert messages["total"] == 1
    assert messages["messages"][0]["role"] == "user"
    assert messages["messages"][0]["message_type"] == "text"
    assert len(factory.instances) == 1
    assert len(factory.instances[0].calls) == 2


def build_test_app(*, settings: Settings, session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    AppStatus.should_exit = False
    AppStatus.should_exit_event = None

    app = FastAPI()
    app.state.sse_manager = SSEManager()
    app.include_router(api_router)

    async def override_db_session() -> Any:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings
    return app


def install_fake_chat_model_factory(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response_batches: list[list[Any]],
) -> FakeChatModelFactory:
    factory = FakeChatModelFactory(response_batches)
    monkeypatch.setattr(llm_module, "create_chat_model", factory)
    return factory


def create_project(client: TestClient, *, name: str) -> dict[str, Any]:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()


def upload_file_via_api(client: TestClient, *, project_id: str, file_path: Path) -> dict[str, Any]:
    with file_path.open("rb") as file_handle:
        response = client.post(
            f"/api/projects/{project_id}/files",
            files={"file": (file_path.name, file_handle, "application/octet-stream")},
        )

    assert response.status_code == 201
    return response.json()


def stream_agent_chat(
    client: TestClient,
    *,
    project_id: str,
    message: str,
    api_key: str = "test-api-key",
) -> tuple[int, dict[str, str], list[dict[str, Any]]]:
    with client.stream(
        "POST",
        f"/api/projects/{project_id}/agent/chat",
        headers={"x-ppt-studio-api-key": api_key},
        json={"message": message},
    ) as response:
        raw_payload = "".join(response.iter_text())
        status_code = response.status_code
        headers = dict(response.headers)

    return status_code, headers, parse_sse_events(raw_payload)


def get_project_detail(client: TestClient, project_id: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    return response.json()


def list_project_files(client: TestClient, project_id: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project_id}/files")
    assert response.status_code == 200
    return response.json()


def list_chat_messages(client: TestClient, project_id: str) -> dict[str, Any]:
    response = client.get(f"/api/projects/{project_id}/chat/messages")
    assert response.status_code == 200
    return response.json()


def update_settings(client: TestClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.put("/api/settings", json=payload)
    assert response.status_code == 200
    return response.json()


def assert_event_order(event_names: list[str], expected_sequence: list[str]) -> None:
    current_index = -1
    for event_name in expected_sequence:
        current_index = event_names.index(event_name, current_index + 1)


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
