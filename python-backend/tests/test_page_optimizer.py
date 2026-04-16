from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from app.agents.page_optimizer import (
    PageOptimizationError,
    build_page_optimization_input,
    optimize_page_code,
)
from app.services.theme_service import ThemeService

ORIGINAL_SFC = """
<script setup lang="ts">
const metrics = [{ label: '营收', value: '12.6M' }]
</script>

<template>
  <main class="slide-page">
    <section class="hero-card">
      <h1 class="page-title">Q1 经营亮点</h1>
      <p class="page-subtitle">核心数据稳定增长</p>
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

.page-title {
  color: var(--slide-text);
}

.page-subtitle {
  color: var(--slide-text-secondary);
}
</style>
""".strip()

OPTIMIZED_SFC = """
<script setup lang="ts">
const metrics = [{ label: '营收', value: '12.6M' }]
</script>

<template>
  <main class="slide-page">
    <section class="hero-card">
      <h1 class="page-title">Q1 经营亮点</h1>
      <p class="page-subtitle">核心数据稳定增长</p>
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

.page-title {
  color: var(--slide-danger);
}

.page-subtitle {
  color: var(--slide-text-secondary);
}
</style>
""".strip()

SYNTHESIZED_SFC = """
<script setup lang="ts">
const metrics = [{ label: '营收', value: '12.6M' }]
</script>

<template>
  <main class="slide-page">
    <section class="hero-card">
      <h1 class="page-title emphasized">Q1 经营亮点</h1>
      <p class="page-subtitle">核心数据稳定增长</p>
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

.page-title {
  color: var(--slide-danger);
}

.emphasized {
  letter-spacing: 0.04em;
}

.page-subtitle {
  color: var(--slide-text-secondary);
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


@pytest.mark.asyncio
async def test_optimize_page_code_updates_title_color_and_returns_change_summary(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)
    fake_model = FakeChatModel([OPTIMIZED_SFC, "标题改为红色强调"])
    events: list[tuple[str, dict[str, Any]]] = []

    optimized_code, change_description = await optimize_page_code(
        project=SimpleNamespace(id="project-1", name="Q1 汇报", description="desc"),
        page=SimpleNamespace(id="page-1", page_number=1, title="经营亮点", page_type="data", version=1, status="generated"),
        page_plan={
            "page_number": 1,
            "title": "经营亮点",
            "type": "data",
            "content_brief": "展示经营亮点",
            "layout": "hero-card",
            "data_refs": [],
        },
        current_page_code=ORIGINAL_SFC,
        user_instruction="把标题改成红色",
        page_chat_history=[{"role": "user", "content": "上一轮先保留版式", "message_type": "text"}],
        theme_config=theme_config,
        model=fake_model,
        sse_callback=collect_events(events),
    )

    assert optimized_code == OPTIMIZED_SFC
    assert change_description == "标题改为红色强调"
    assert [event for event, _ in events][:2] == ["thinking", "page_optimizing"]
    assert len(fake_model.calls) == 2


@pytest.mark.asyncio
async def test_optimize_page_code_runs_deliberation_flow(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)
    fake_model = FakeChatModel([OPTIMIZED_SFC, "标题改色后还可以强化聚焦感。", SYNTHESIZED_SFC, "标题改红并增强聚焦"])
    events: list[tuple[str, dict[str, Any]]] = []

    optimized_code, change_description = await optimize_page_code(
        project=SimpleNamespace(id="project-1", name="Q1 汇报", description="desc"),
        page=SimpleNamespace(id="page-1", page_number=1, title="经营亮点", page_type="data", version=1, status="generated"),
        page_plan=None,
        current_page_code=ORIGINAL_SFC,
        user_instruction="把标题改成红色并更醒目一点",
        page_chat_history=[],
        theme_config=theme_config,
        model=fake_model,
        deliberation_enabled=True,
        sse_callback=collect_events(events),
    )

    event_names = [event for event, _ in events]
    assert optimized_code == SYNTHESIZED_SFC
    assert change_description == "标题改红并增强聚焦"
    assert "deliberation_started" in event_names
    assert event_names.count("deliberation_round") == 3
    assert "deliberation_summary" in event_names


@pytest.mark.asyncio
async def test_optimize_page_code_falls_back_to_draft_when_deliberation_fails(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)
    fake_model = FakeChatModel([OPTIMIZED_SFC, RuntimeError("critic failed"), "标题改为红色"])
    events: list[tuple[str, dict[str, Any]]] = []

    optimized_code, change_description = await optimize_page_code(
        project=SimpleNamespace(id="project-1", name="Q1 汇报", description="desc"),
        page=SimpleNamespace(id="page-1", page_number=1, title="经营亮点", page_type="data", version=1, status="generated"),
        page_plan=None,
        current_page_code=ORIGINAL_SFC,
        user_instruction="把标题改成红色",
        page_chat_history=[],
        theme_config=theme_config,
        model=fake_model,
        deliberation_enabled=True,
        sse_callback=collect_events(events),
    )

    assert optimized_code == OPTIMIZED_SFC
    assert change_description == "标题改为红色"
    assert events[-1][0] == "deliberation_summary"
    assert "回退到 Draft 优化结果" in str(events[-1][1]["summary"])


@pytest.mark.asyncio
async def test_optimize_page_code_repairs_invalid_output(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)
    fake_model = FakeChatModel(["plain text", OPTIMIZED_SFC, "标题改为红色"])

    optimized_code, change_description = await optimize_page_code(
        project=SimpleNamespace(id="project-1", name="Q1 汇报", description="desc"),
        page=SimpleNamespace(id="page-1", page_number=1, title="经营亮点", page_type="data", version=1, status="generated"),
        page_plan=None,
        current_page_code=ORIGINAL_SFC,
        user_instruction="把标题改成红色",
        page_chat_history=[],
        theme_config=theme_config,
        model=fake_model,
    )

    assert optimized_code == OPTIMIZED_SFC
    assert change_description == "标题改为红色"
    assert len(fake_model.calls) == 3


@pytest.mark.asyncio
async def test_optimize_page_code_rejects_blank_current_code(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)

    with pytest.raises(PageOptimizationError):
        await optimize_page_code(
            project=SimpleNamespace(id="project-1", name="Q1 汇报", description="desc"),
            page=SimpleNamespace(id="page-1", page_number=1, title="经营亮点", page_type="data", version=1, status="generated"),
            page_plan=None,
            current_page_code="   ",
            user_instruction="把标题改成红色",
            page_chat_history=[],
            theme_config=theme_config,
            model=FakeChatModel([]),
        )


def test_build_page_optimization_input_keeps_recent_history_only(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)
    payload = build_page_optimization_input(
        project=SimpleNamespace(id="project-1", name="Q1 汇报", description="desc"),
        page=SimpleNamespace(id="page-1", page_number=2, title="经营亮点", page_type="data", version=3, status="generated"),
        page_plan=None,
        current_page_code=ORIGINAL_SFC,
        user_instruction="把标题改成红色",
        page_chat_history=[{"role": "user", "content": f"msg-{index}"} for index in range(25)],
        theme_config=theme_config,
    )

    assert payload["page"]["page_number"] == 2
    assert len(payload["page_chat_history"]) == 20
    assert payload["page_chat_history"][0]["content"] == "msg-5"


def collect_events(events: list[tuple[str, dict[str, Any]]]):
    async def _callback(event: str, data: dict[str, Any]) -> None:
        events.append((event, data))

    return _callback
