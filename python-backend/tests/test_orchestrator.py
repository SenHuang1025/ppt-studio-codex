from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from app.agents.orchestrator import determine_route
from app.agents.state import ProjectState
from app.schemas import AppTheme, LLMProvider, SettingsResponse


async def noop_sse_callback(_event: str, _data: dict[str, Any]) -> None:
    return None


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


def build_state(
    *,
    user_message: str,
    uploaded_files: list[Any] | None = None,
    existing_outline: dict[str, Any] | None = None,
    chat_history: list[dict[str, Any]] | None = None,
) -> ProjectState:
    settings = SettingsResponse(
        llm_provider=LLMProvider.OPENAI,
        model_name="fake-model",
        api_base_url="https://example.com/v1",
        multi_agent_deliberation_enabled=False,
        default_theme=AppTheme.WARM_PAPER,
        storage_path="E:/tmp/projects",
    )
    project = SimpleNamespace(name="Demo Project", description=None, status="draft", outline=existing_outline)
    return ProjectState(
        project_id="project-1",
        user_message=user_message,
        page_number=None,
        chat_history=chat_history or [],
        uploaded_files=uploaded_files or [],
        parsed_contents=[],
        outline=existing_outline,
        current_phase="chatting",
        current_page=None,
        deliberation_enabled=False,
        deliberation_target=None,
        deliberation_trace=[],
        sse_callback=noop_sse_callback,
        project=project,
        route=None,
        route_decision=None,
        assistant_message=None,
        direct_reply=None,
        settings=settings,
        analysis_summaries=[],
        errors=[],
        existing_outline=existing_outline,
        post_analyze_route=None,
        draft_outline=None,
        persistable_assistant_message=None,
    )


def test_orchestrator_prefers_analyze_when_pending_files_exist() -> None:
    state = build_state(
        user_message="请根据资料做一个销售汇报 PPT 大纲",
        uploaded_files=[{"id": "file-1", "parse_status": "pending", "parsed_content": None}],
    )

    decision = asyncio.run(determine_route(state))

    assert decision.route == "analyze"
    assert decision.followup_route == "plan"


def test_orchestrator_routes_to_plan_for_ppt_request() -> None:
    state = build_state(user_message="帮我规划一份产品发布会 PPT 大纲")

    decision = asyncio.run(determine_route(state))

    assert decision.route == "plan"


def test_orchestrator_routes_to_chat_for_small_talk() -> None:
    state = build_state(user_message="你好，你现在能做什么？")

    decision = asyncio.run(determine_route(state))

    assert decision.route == "chat"


def test_orchestrator_routes_outline_adjustment_to_plan() -> None:
    state = build_state(
        user_message="把现有大纲重排一下，减少一页目录，新增一页风险提示",
        existing_outline={
            "title": "Existing Outline",
            "total_pages": 3,
            "theme_suggestion": "warm-paper",
            "pages": [],
        },
    )

    decision = asyncio.run(determine_route(state))

    assert decision.route == "plan"


def test_orchestrator_llm_prompt_receives_chat_history() -> None:
    state = build_state(
        user_message="继续吧",
        chat_history=[
            {
                "role": "user",
                "content": "请先帮我规划一份经营汇报",
                "message_type": "text",
                "page_number": None,
                "metadata": None,
            },
            {
                "role": "assistant",
                "content": "已生成《经营汇报》共 5 页大纲。",
                "message_type": "outline",
                "page_number": None,
                "metadata": {"outline_title": "经营汇报", "total_pages": 5},
            },
        ],
    )
    model = FakeChatModel(
        ['{"route":"plan","reason":"根据历史可判断用户要继续调整大纲","followup_route":null,"unsupported_capability":null}']
    )

    decision = asyncio.run(determine_route(state, model=model))

    assert decision.route == "plan"
    assert len(model.calls) == 1
    assert "请先帮我规划一份经营汇报" in model.calls[0][1][1]
    assert "已生成《经营汇报》共 5 页大纲。" in model.calls[0][1][1]
