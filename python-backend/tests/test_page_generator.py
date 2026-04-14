from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.agents.page_generator import (
    PageGenerationValidationError,
    extract_vue_sfc,
    generate_page_code,
)
from app.schemas.project import OutlinePageSchema
from app.services.theme_service import ThemeService

VALID_SFC = """
<script setup lang="ts">
const metrics = [
  { label: 'Revenue', value: '$18.6M', trend: '+12%' }
]
</script>

<template>
  <main class="slide-page">
    <section class="hero">
      <h1>Q1 经营概览</h1>
      <IconCard
        v-for="metric in metrics"
        :key="metric.label"
        :icon="'📈'"
        :label="metric.label"
        :trend="metric.trend"
        :value="metric.value"
      />
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

SYNTHESIZED_SFC = """
<script setup lang="ts">
const agenda = ['经营结果', '关键动作', '下季度计划']
</script>

<template>
  <main class="slide-page">
    <section class="hero">
      <h1>Q1 汇报目录</h1>
      <ul>
        <li v-for="item in agenda" :key="item">{{ item }}</li>
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


@pytest.mark.asyncio
async def test_generate_page_code_succeeds_with_single_draft(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)
    fake_model = FakeChatModel([VALID_SFC])
    events: list[tuple[str, dict[str, Any]]] = []

    page_code = await generate_page_code(
        project=type("Project", (), {"id": "project-1", "name": "Q1 汇报", "description": "desc"})(),
        outline_page=build_outline_page(page_type="data"),
        parsed_contents=[build_parsed_content()],
        theme_config=theme_config,
        current_page_number=2,
        total_pages=5,
        existing_page_code=None,
        model=fake_model,
        sse_callback=collect_events(events),
    )

    assert "<template>" in page_code
    assert '<script setup lang="ts">' in page_code
    assert [event for event, _ in events][:2] == ["thinking", "page_generating"]
    assert len(fake_model.calls) == 1


@pytest.mark.asyncio
async def test_generate_page_code_extracts_fenced_sfc(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)
    fake_model = FakeChatModel([f"这里是页面代码：\n```vue\n{VALID_SFC}\n```\n请查收。"])

    page_code = await generate_page_code(
        project=type("Project", (), {"id": "project-1", "name": "Q1 汇报", "description": None})(),
        outline_page=build_outline_page(),
        parsed_contents=[build_parsed_content()],
        theme_config=theme_config,
        current_page_number=1,
        total_pages=3,
        existing_page_code=None,
        model=fake_model,
    )

    assert page_code == VALID_SFC


@pytest.mark.asyncio
async def test_generate_page_code_repairs_invalid_initial_output(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)
    fake_model = FakeChatModel(["not a vue page", VALID_SFC])

    page_code = await generate_page_code(
        project=type("Project", (), {"id": "project-1", "name": "Q1 汇报", "description": None})(),
        outline_page=build_outline_page(),
        parsed_contents=[build_parsed_content()],
        theme_config=theme_config,
        current_page_number=1,
        total_pages=3,
        existing_page_code=None,
        model=fake_model,
    )

    assert page_code == VALID_SFC
    assert len(fake_model.calls) == 2


@pytest.mark.asyncio
async def test_generate_page_code_runs_deliberation_flow(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)
    fake_model = FakeChatModel([VALID_SFC, "目录页的层次可以更清晰。", SYNTHESIZED_SFC])
    events: list[tuple[str, dict[str, Any]]] = []

    page_code = await generate_page_code(
        project=type("Project", (), {"id": "project-1", "name": "Q1 汇报", "description": None})(),
        outline_page=build_outline_page(page_type="toc", page_number=2, title="目录"),
        parsed_contents=[build_parsed_content()],
        theme_config=theme_config,
        current_page_number=2,
        total_pages=3,
        existing_page_code=None,
        model=fake_model,
        deliberation_enabled=True,
        sse_callback=collect_events(events),
    )

    event_names = [event for event, _ in events]
    assert page_code == SYNTHESIZED_SFC
    assert len(fake_model.calls) == 3
    assert "deliberation_started" in event_names
    assert event_names.count("deliberation_round") == 3
    assert "deliberation_summary" in event_names


@pytest.mark.asyncio
async def test_generate_page_code_falls_back_to_draft_when_deliberation_fails(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)
    fake_model = FakeChatModel([VALID_SFC, RuntimeError("critic failed")])
    events: list[tuple[str, dict[str, Any]]] = []

    page_code = await generate_page_code(
        project=type("Project", (), {"id": "project-1", "name": "Q1 汇报", "description": None})(),
        outline_page=build_outline_page(page_type="comparison"),
        parsed_contents=[build_parsed_content()],
        theme_config=theme_config,
        current_page_number=2,
        total_pages=3,
        existing_page_code=None,
        model=fake_model,
        deliberation_enabled=True,
        sse_callback=collect_events(events),
    )

    assert page_code == VALID_SFC
    assert events[-1][0] == "deliberation_summary"
    assert "回退到 Draft 页面" in str(events[-1][1]["summary"])


@pytest.mark.asyncio
async def test_generate_page_code_repairs_missing_template_or_script(settings) -> None:
    theme_config = ThemeService(settings=settings).resolve_theme(None)
    fake_model = FakeChatModel(
        [
            "<script setup lang=\"ts\">const x = 1</script>",
            VALID_SFC,
        ]
    )

    page_code = await generate_page_code(
        project=type("Project", (), {"id": "project-1", "name": "Q1 汇报", "description": None})(),
        outline_page=build_outline_page(page_type="content"),
        parsed_contents=[build_parsed_content()],
        theme_config=theme_config,
        current_page_number=3,
        total_pages=3,
        existing_page_code=None,
        model=fake_model,
    )

    assert page_code == VALID_SFC


def test_extract_vue_sfc_raises_for_missing_sfc() -> None:
    with pytest.raises(PageGenerationValidationError):
        extract_vue_sfc("plain text only")


def build_outline_page(
    *,
    page_number: int = 1,
    page_type: str = "cover",
    title: str = "Q1 汇报封面",
) -> OutlinePageSchema:
    return OutlinePageSchema(
        page_number=page_number,
        title=title,
        type=page_type,
        content_brief="概述本页重点",
        layout="center-hero",
        data_refs=["metrics.csv"],
    )


def build_parsed_content() -> dict[str, Any]:
    return {
        "file_id": "file-1",
        "file_name": "metrics.csv",
        "file_type": "csv",
        "summary": "营收、利润率和客户增长数据已经整理。",
        "key_points": ["营收增长 12%", "客户增长 8%"],
        "structured_data": {"columns": ["month", "revenue"]},
        "text_content": "January revenue 12.1, February revenue 12.8",
    }


def collect_events(events: list[tuple[str, dict[str, Any]]]):
    async def _callback(event: str, data: dict[str, Any]) -> None:
        events.append((event, data))

    return _callback
