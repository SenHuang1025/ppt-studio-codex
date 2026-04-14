from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from app.agents.planner import deliberate_plan_node, generate_outline_draft, planner_node
from app.agents.state import ProjectState
from app.schemas import AppTheme, LLMProvider, SettingsResponse


VALID_DRAFT_JSON = """
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

SYNTHESIS_JSON = """
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
        self._responses = responses
        self.calls: list[Any] = []

    async def ainvoke(self, messages: Any) -> FakeModelResponse:
        self.calls.append(messages)
        if not self._responses:
            raise AssertionError("Fake model received more calls than configured.")

        next_response = self._responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return FakeModelResponse(content=next_response)


class FakeProjectService:
    def __init__(self) -> None:
        self.saved_outlines: list[dict[str, Any]] = []

    async def save_outline(self, project_id: str, outline: Any) -> None:
        outline_payload = outline.model_dump(mode="json") if hasattr(outline, "model_dump") else outline
        self.saved_outlines.append({"project_id": project_id, "outline": outline_payload})


class EventRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, event: str, data: dict[str, Any]) -> None:
        self.events.append((event, data))


def build_state(*, deliberation_enabled: bool) -> tuple[ProjectState, EventRecorder]:
    recorder = EventRecorder()
    settings = SettingsResponse(
        llm_provider=LLMProvider.OPENAI,
        model_name="fake-model",
        api_base_url="https://example.com/v1",
        multi_agent_deliberation_enabled=deliberation_enabled,
        default_theme=AppTheme.WARM_PAPER,
        storage_path="E:/tmp/projects",
    )
    project = SimpleNamespace(name="Demo Project", description="Quarterly planning", status="draft", outline=None)
    state = ProjectState(
        project_id="project-1",
        user_message="请根据资料规划一份季度经营汇报 PPT",
        page_number=None,
        chat_history=[
            {
                "role": "user",
                "content": "上一轮请重点突出经营亮点",
                "message_type": "text",
                "page_number": None,
                "metadata": None,
            },
            {
                "role": "assistant",
                "content": "已生成《经营汇报草案》共 3 页大纲。",
                "message_type": "outline",
                "page_number": None,
                "metadata": {"outline_title": "经营汇报草案", "total_pages": 3},
            },
        ],
        uploaded_files=[],
        parsed_contents=[
            {
                "file_id": "file-1",
                "file_name": "brief.txt",
                "file_type": "txt",
                "summary": "包含经营数据和下一步计划。",
                "key_points": ["营收增长", "客户续约率提升"],
                "structured_data": {"sections": ["营收", "计划"]},
            }
        ],
        outline=None,
        current_phase="chatting",
        current_page=None,
        deliberation_enabled=deliberation_enabled,
        deliberation_target=None,
        deliberation_trace=[],
        sse_callback=recorder,
        project=project,
        route="plan",
        route_decision=None,
        assistant_message=None,
        direct_reply=None,
        settings=settings,
        analysis_summaries=["brief.txt: 包含经营数据和下一步计划。"],
        errors=[],
        existing_outline=None,
        post_analyze_route=None,
        draft_outline=None,
        persistable_assistant_message=None,
    )
    return state, recorder


def test_planner_validates_outline_schema() -> None:
    state, _ = build_state(deliberation_enabled=False)
    model = FakeChatModel([VALID_DRAFT_JSON])

    outline = asyncio.run(generate_outline_draft(state, model=model))

    assert outline.total_pages == 3
    assert [page.page_number for page in outline.pages] == [1, 2, 3]
    assert outline.pages[1].type == "keypoints"


def test_planner_repairs_invalid_output() -> None:
    state, _ = build_state(deliberation_enabled=False)
    model = FakeChatModel(["not-json-at-all", VALID_DRAFT_JSON])

    outline = asyncio.run(generate_outline_draft(state, model=model))

    assert outline.total_pages == 3
    assert len(model.calls) == 2


def test_planner_prompt_receives_chat_history() -> None:
    state, _ = build_state(deliberation_enabled=False)
    model = FakeChatModel([VALID_DRAFT_JSON])

    outline = asyncio.run(generate_outline_draft(state, model=model))

    assert outline.total_pages == 3
    assert "上一轮请重点突出经营亮点" in model.calls[0][1][1]
    assert "已生成《经营汇报草案》共 3 页大纲。" in model.calls[0][1][1]


def test_planner_node_skips_deliberation_when_disabled() -> None:
    state, recorder = build_state(deliberation_enabled=False)
    model = FakeChatModel([VALID_DRAFT_JSON])
    project_service = FakeProjectService()

    next_state = asyncio.run(planner_node(state, model=model, project_service=project_service))

    assert next_state["outline"] is not None
    assert next_state["draft_outline"] is not None
    assert [event for event, _ in recorder.events] == ["thinking", "outline"]
    assert project_service.saved_outlines[0]["outline"]["total_pages"] == 3


def test_planner_deliberation_runs_draft_critic_synthesis() -> None:
    state, recorder = build_state(deliberation_enabled=True)
    project_service = FakeProjectService()
    model = FakeChatModel([VALID_DRAFT_JSON, "目录略少，建议补一页提纲，增强叙事起承转合。", SYNTHESIS_JSON])

    state = asyncio.run(planner_node(state, model=model, project_service=project_service))
    state = asyncio.run(deliberate_plan_node(state, model=model, project_service=project_service))

    event_names = [event for event, _ in recorder.events]
    deliberation_roles = [data["role"] for event, data in recorder.events if event == "deliberation_round"]

    assert event_names == [
        "thinking",
        "deliberation_started",
        "deliberation_round",
        "deliberation_round",
        "deliberation_round",
        "deliberation_summary",
        "outline",
    ]
    assert deliberation_roles == ["draft", "critic", "synthesis"]
    assert state["outline"] is not None
    assert state["outline"]["total_pages"] == 4
    assert project_service.saved_outlines[0]["outline"]["title"] == "Q1 经营汇报（优化版）"


def test_planner_deliberation_falls_back_to_draft_when_subflow_fails() -> None:
    state, recorder = build_state(deliberation_enabled=True)
    project_service = FakeProjectService()
    model = FakeChatModel([VALID_DRAFT_JSON, RuntimeError("critic failed")])

    state = asyncio.run(planner_node(state, model=model, project_service=project_service))
    state = asyncio.run(deliberate_plan_node(state, model=model, project_service=project_service))

    assert state["outline"] is not None
    assert state["outline"]["title"] == "Q1 经营汇报"
    assert recorder.events[-2] == (
        "deliberation_summary",
        {"target": "planner", "summary": "思辨子流程失败，已回退到 Draft 大纲。"},
    )
    assert project_service.saved_outlines[0]["outline"]["total_pages"] == 3
