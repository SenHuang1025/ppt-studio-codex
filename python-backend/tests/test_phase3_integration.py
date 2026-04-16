from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sse_starlette.sse import AppStatus

import app.agents.llm as llm_module
from app.agents.llm import LLMRuntimeConfig
from app.agents.page_generator import validate_vue_sfc
from app.api.router import router as api_router
from app.config import Settings, get_settings
from app.db import get_db_session
from app.models import ProjectPage
from app.schemas import LLMProvider, OutlinePageSchema, OutlineSchema, SettingsResponse
from app.services import SSEManager
from tests.sample_files import write_excel_file

FILE_ANALYZER_RESPONSE = """
{
  "summary": "材料展示了季度经营回顾、关键指标和下一步计划，适合整理成经营汇报。",
  "key_points": ["营收增长", "重点项目推进", "需要给出下季度行动"]
}
""".strip()

PHASE3_MAIN_PAGE_SPECS = (
    {
        "title": "季度经营汇报",
        "type": "cover",
        "content_brief": "经营汇报封面页",
        "layout": "center-hero",
        "data_refs": [],
        "variant": "cover",
    },
    {
        "title": "核心结论",
        "type": "keypoints",
        "content_brief": "总结季度的三项核心判断",
        "layout": "bullet-grid",
        "data_refs": ["sales.xlsx"],
        "variant": "metrics",
    },
    {
        "title": "增长趋势",
        "type": "data",
        "content_brief": "用图表说明营收与交付节奏变化",
        "layout": "chart-focus",
        "data_refs": ["sales.xlsx"],
        "variant": "chart",
    },
    {
        "title": "重点账户",
        "type": "data",
        "content_brief": "列出重点客户与跟进重点",
        "layout": "table-focus",
        "data_refs": ["sales.xlsx"],
        "variant": "table",
    },
    {
        "title": "下一步计划",
        "type": "ending",
        "content_brief": "收束并给出下季度行动安排",
        "layout": "title-body",
        "data_refs": [],
        "variant": "ending",
    },
)

PHASE3_MAIN_OUTLINE_RESPONSE = json.dumps(
    {
        "title": "季度经营汇报",
        "total_pages": len(PHASE3_MAIN_PAGE_SPECS),
        "theme_suggestion": "warm-orange",
        "pages": [
            {
                "page_number": index,
                "title": page["title"],
                "type": page["type"],
                "content_brief": page["content_brief"],
                "layout": page["layout"],
                "data_refs": list(page["data_refs"]),
            }
            for index, page in enumerate(PHASE3_MAIN_PAGE_SPECS, start=1)
        ],
    },
    ensure_ascii=False,
)


@dataclass
class FakeModelResponse:
    content: str


class FakeChatModel:
    def __init__(self, *, responses: list[Any], runtime_config: LLMRuntimeConfig) -> None:
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
        self.runtime_configs: list[LLMRuntimeConfig] = []

    def __call__(self, config: LLMRuntimeConfig) -> FakeChatModel:
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


def build_local_settings(settings: Settings) -> Settings:
    preview_root = settings.backend_dir / "preview-server"
    local_settings = settings.model_copy(
        update={
            "preview_server_dir": preview_root,
            "preview_slides_dir": preview_root / "src" / "slides",
            "preview_theme_file_override": preview_root / "src" / "theme" / "variables.css",
        }
    )
    local_settings.ensure_directories()
    return local_settings


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


def stream_confirm_outline(
    client: TestClient,
    *,
    project_id: str,
    outline: OutlineSchema | None = None,
    api_key: str = "test-api-key",
) -> tuple[int, dict[str, str], list[dict[str, Any]]]:
    payload = {"outline": outline.model_dump(mode="json")} if outline is not None else {}

    with client.stream(
        "POST",
        f"/api/projects/{project_id}/agent/confirm-outline",
        headers={"x-ppt-studio-api-key": api_key},
        json=payload,
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


def update_settings(client: TestClient, payload: dict[str, Any]) -> SettingsResponse:
    response = client.put("/api/settings", json=payload)
    assert response.status_code == 200
    return SettingsResponse.model_validate(response.json())


def load_project_pages(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    project_id: str,
) -> list[ProjectPage]:
    async def _load() -> list[ProjectPage]:
        async with session_factory() as session:
            stmt: Select[tuple[ProjectPage]] = (
                select(ProjectPage)
                .options(selectinload(ProjectPage.versions))
                .where(ProjectPage.project_id == project_id)
                .order_by(ProjectPage.page_number.asc())
            )
            return list((await session.execute(stmt)).scalars().all())

    return asyncio.run(_load())


def assert_preview_files_match(*, settings: Settings, page_codes: list[str]) -> None:
    for page_number, page_code in enumerate(page_codes, start=1):
        preview_file = settings.preview_slides_dir_path / f"page-{page_number}.vue"
        assert preview_file.exists()
        written_code = preview_file.read_text(encoding="utf-8")
        validate_vue_sfc(written_code)
        assert written_code == page_code


def build_outline(title: str, page_specs: tuple[dict[str, Any], ...]) -> OutlineSchema:
    return OutlineSchema(
        title=title,
        total_pages=len(page_specs),
        theme_suggestion="warm-orange",
        pages=[
            OutlinePageSchema(
                page_number=index,
                title=page["title"],
                type=page["type"],
                content_brief=page["content_brief"],
                layout=page["layout"],
                data_refs=list(page["data_refs"]),
            )
            for index, page in enumerate(page_specs, start=1)
        ],
    )


def build_smoke_outline(*, page_count: int) -> OutlineSchema:
    variant_cycle = ("cover", "content", "metrics", "chart", "table", "ending")
    page_specs: list[dict[str, Any]] = []

    for page_number in range(1, page_count + 1):
        variant = variant_cycle[(page_number - 1) % len(variant_cycle)]
        page_specs.append(
            {
                "title": f"第 {page_number} 页",
                "type": "data" if variant in {"chart", "table"} else ("cover" if variant == "cover" else "content"),
                "content_brief": f"第 {page_number} 页 smoke 验证",
                "layout": f"{variant}-layout",
                "data_refs": ["sales.xlsx"] if variant in {"metrics", "chart", "table"} else [],
                "variant": variant,
            }
        )

    return build_outline("16 页稳定性验证", tuple(page_specs))


def responses_for_page_specs(page_specs: tuple[dict[str, Any], ...]) -> list[str]:
    outline = build_outline("phase3", page_specs)
    return responses_for_outline(outline)


def responses_for_outline(outline: OutlineSchema) -> list[str]:
    return [response_for_outline_page(page) for page in outline.pages]


def format_ts_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


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


def assert_event_order(event_names: list[str], expected_sequence: list[str]) -> None:
    current_index = -1
    for event_name in expected_sequence:
        current_index = event_names.index(event_name, current_index + 1)


def response_for_outline_page(outline_page: OutlinePageSchema) -> str:
    variant = resolve_variant(outline_page)

    if variant == "cover":
        return build_cover_sfc(
            title=outline_page.title,
            subtitle=outline_page.content_brief,
        )
    if variant == "metrics":
        return build_metrics_sfc(
            title=outline_page.title,
            lead=outline_page.content_brief,
            score=84,
            progress_items=[
                {"color": "var(--slide-primary)", "label": "营收质量", "value": 86},
                {"color": "var(--slide-secondary)", "label": "项目推进", "value": 79},
                {"color": "var(--slide-accent)", "label": "交付稳定性", "value": 82},
            ],
        )
    if variant == "chart":
        return build_chart_sfc(
            title=outline_page.title,
            summary=outline_page.content_brief,
            series_name="营收指数",
            values=[72, 78, 84, 91],
        )
    if variant == "table":
        return build_table_sfc(
            title=outline_page.title,
            summary=outline_page.content_brief,
        )
    if variant == "ending":
        return build_ending_sfc(
            title=outline_page.title,
            bullets=["收束本次结论", "明确负责人", "约定下一轮复盘时间"],
        )
    return build_content_sfc(
        title=outline_page.title,
        paragraphs=[
            outline_page.content_brief,
            "本页使用稳定的纯内容布局，确保预览沙箱可以接收常规文字型页面。",
        ],
    )


def resolve_variant(outline_page: OutlinePageSchema) -> str:
    title = outline_page.title
    layout = outline_page.layout.lower()
    page_type = outline_page.type.lower()

    if "cover" in page_type or "hero" in layout or "封面" in title:
        return "cover"
    if "table" in layout or "账户" in title:
        return "table"
    if "chart" in layout or "趋势" in title:
        return "chart"
    if "keypoints" in page_type or "summary" in layout or "metrics" in layout or "结论" in title or "摘要" in title:
        return "metrics"
    if "ending" in page_type or "ending" in layout or "计划" in title:
        return "ending"
    return "content"


def build_cover_sfc(*, title: str, subtitle: str) -> str:
    return dedent(
        f"""
        <script setup lang="ts">
        const tags = ['Phase 3 integration', 'Deterministic fixture', 'Preview-safe SFC']
        </script>

        <template>
          <main class="slide-page">
            <section class="hero-card">
              <p class="eyebrow">PPT Studio</p>
              <h1>{title}</h1>
              <p class="subtitle">{subtitle}</p>
              <div class="tag-row">
                <span v-for="tag in tags" :key="tag" class="tag">{{{{ tag }}}}</span>
              </div>
            </section>
          </main>
        </template>

        <style scoped>
        .slide-page {{
          width: 1920px;
          height: 1080px;
          overflow: hidden;
          display: grid;
          place-items: center;
          padding: 80px;
          background:
            radial-gradient(circle at top left, var(--slide-secondary-soft) 0%, transparent 34%),
            linear-gradient(180deg, var(--slide-bg) 0%, color-mix(in srgb, var(--slide-surface) 72%, var(--slide-bg) 28%) 100%);
          color: var(--slide-text);
          font-family: var(--slide-font-body);
        }}

        .hero-card {{
          width: min(1320px, 100%);
          padding: 88px 96px;
          border: 1px solid color-mix(in srgb, var(--slide-border) 78%, transparent);
          border-radius: var(--slide-radius-xl);
          background: var(--slide-surface-strong);
          box-shadow: var(--slide-shadow);
        }}

        .eyebrow {{
          margin: 0 0 18px;
          color: var(--slide-text-secondary);
          font-size: 18px;
          letter-spacing: 0.22em;
          text-transform: uppercase;
        }}

        h1 {{
          margin: 0;
          font-family: var(--slide-font-title);
          font-size: 84px;
          line-height: 1.04;
          letter-spacing: -0.05em;
        }}

        .subtitle {{
          margin: 22px 0 0;
          max-width: 860px;
          color: var(--slide-text-secondary);
          font-size: 28px;
          line-height: 1.7;
        }}

        .tag-row {{
          display: flex;
          flex-wrap: wrap;
          gap: 14px;
          margin-top: 34px;
        }}

        .tag {{
          display: inline-flex;
          align-items: center;
          min-height: 42px;
          padding: 0 18px;
          border-radius: 999px;
          background: var(--slide-primary-soft);
          color: var(--slide-primary);
          font-size: 15px;
          font-weight: 700;
        }}
        </style>
        """
    ).strip()


def build_content_sfc(*, title: str, paragraphs: list[str]) -> str:
    return dedent(
        f"""
        <script setup lang="ts">
        const paragraphs: string[] = {format_ts_json(paragraphs)}
        </script>

        <template>
          <main class="slide-page">
            <section class="content-card">
              <p class="eyebrow">Content Page</p>
              <h1>{title}</h1>
              <p v-for="paragraph in paragraphs" :key="paragraph" class="paragraph">{{{{ paragraph }}}}</p>
            </section>
          </main>
        </template>

        <style scoped>
        .slide-page {{
          width: 1920px;
          height: 1080px;
          overflow: hidden;
          padding: 82px 88px;
          background:
            radial-gradient(circle at 82% 18%, var(--slide-accent-soft) 0%, transparent 20%),
            linear-gradient(180deg, var(--slide-bg) 0%, color-mix(in srgb, var(--slide-surface) 70%, var(--slide-bg) 30%) 100%);
          color: var(--slide-text);
          font-family: var(--slide-font-body);
        }}

        .content-card {{
          display: grid;
          gap: 22px;
          width: min(1280px, 100%);
          padding: 56px 62px;
          border: 1px solid color-mix(in srgb, var(--slide-border) 78%, transparent);
          border-radius: var(--slide-radius-xl);
          background: var(--slide-surface-strong);
          box-shadow: var(--slide-shadow-soft);
        }}

        .eyebrow {{
          margin: 0;
          color: var(--slide-text-secondary);
          font-size: 16px;
          letter-spacing: 0.2em;
          text-transform: uppercase;
        }}

        h1 {{
          margin: 0;
          font-family: var(--slide-font-title);
          font-size: 62px;
          line-height: 1.08;
          letter-spacing: -0.04em;
        }}

        .paragraph {{
          margin: 0;
          color: var(--slide-text-secondary);
          font-size: 26px;
          line-height: 1.78;
        }}
        </style>
        """
    ).strip()


def build_metrics_sfc(*, title: str, lead: str, score: int, progress_items: list[dict[str, Any]]) -> str:
    return dedent(
        f"""
        <script setup lang="ts">
        type ProgressItem = {{
          color: string
          label: string
          value: number
        }}

        const score = {score}
        const progressItems: ProgressItem[] = {format_ts_json(progress_items)}
        </script>

        <template>
          <main class="slide-page">
            <section class="hero-panel">
              <div>
                <p class="eyebrow">Key Metrics</p>
                <h1>{title}</h1>
                <p class="lead">{lead}</p>
              </div>
              <div class="score-shell">
                <CountUp :duration="1.4" :end="score" suffix="%" />
              </div>
            </section>

            <section class="progress-panel">
              <ProgressBar
                v-for="item in progressItems"
                :key="item.label"
                :animated="true"
                :color="item.color"
                :label="item.label"
                :value="item.value"
              />
            </section>
          </main>
        </template>

        <style scoped>
        .slide-page {{
          width: 1920px;
          height: 1080px;
          overflow: hidden;
          display: grid;
          grid-template-rows: auto 1fr;
          gap: 28px;
          padding: 72px 78px;
          background:
            radial-gradient(circle at top left, var(--slide-secondary-soft) 0%, transparent 34%),
            linear-gradient(180deg, var(--slide-bg) 0%, color-mix(in srgb, var(--slide-surface) 70%, var(--slide-bg) 30%) 100%);
          color: var(--slide-text);
          font-family: var(--slide-font-body);
        }}

        .hero-panel,
        .progress-panel {{
          border: 1px solid color-mix(in srgb, var(--slide-border) 78%, transparent);
          border-radius: var(--slide-radius-xl);
          background: var(--slide-surface-strong);
          box-shadow: var(--slide-shadow-soft);
        }}

        .hero-panel {{
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 24px;
          padding: 38px 42px;
        }}

        .eyebrow {{
          margin: 0 0 16px;
          color: var(--slide-text-secondary);
          font-size: 15px;
          letter-spacing: 0.2em;
          text-transform: uppercase;
        }}

        h1 {{
          margin: 0;
          font-family: var(--slide-font-title);
          font-size: 62px;
          line-height: 1.08;
          letter-spacing: -0.04em;
        }}

        .lead {{
          margin: 18px 0 0;
          max-width: 980px;
          color: var(--slide-text-secondary);
          font-size: 24px;
          line-height: 1.74;
        }}

        .score-shell {{
          min-width: 220px;
          padding: 20px 24px;
          border-radius: var(--slide-radius-lg);
          background: var(--slide-primary-soft);
          color: var(--slide-primary);
          font-family: var(--slide-font-title);
          font-size: 72px;
          line-height: 1;
          text-align: right;
        }}

        .progress-panel {{
          display: grid;
          gap: 20px;
          padding: 34px 38px;
        }}
        </style>
        """
    ).strip()


def build_chart_sfc(*, title: str, summary: str, series_name: str, values: list[int]) -> str:
    option = {
        "legend": {"top": 0},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": ["Q1", "Q2", "Q3", "Q4"]},
        "yAxis": {"type": "value", "splitNumber": 4},
        "series": [
            {
                "name": series_name,
                "type": "line",
                "smooth": True,
                "data": values,
                "lineStyle": {"width": 4},
                "areaStyle": {"opacity": 0.16},
            }
        ],
    }
    return dedent(
        f"""
        <script setup lang="ts">
        import type {{ EChartsOption }} from 'echarts'

        const option: EChartsOption = {format_ts_json(option)}
        </script>

        <template>
          <main class="slide-page">
            <section class="header">
              <p class="eyebrow">Trend View</p>
              <h1>{title}</h1>
              <p class="summary">{summary}</p>
            </section>
            <section class="chart-card">
              <AnimatedChart :animation-delay="100" :option="option" />
            </section>
          </main>
        </template>

        <style scoped>
        .slide-page {{
          width: 1920px;
          height: 1080px;
          overflow: hidden;
          display: grid;
          grid-template-rows: auto 1fr;
          gap: 28px;
          padding: 72px 78px;
          background:
            radial-gradient(circle at 85% 18%, var(--slide-accent-soft) 0%, transparent 20%),
            linear-gradient(180deg, var(--slide-bg) 0%, color-mix(in srgb, var(--slide-surface) 70%, var(--slide-bg) 30%) 100%);
          color: var(--slide-text);
          font-family: var(--slide-font-body);
        }}

        .header,
        .chart-card {{
          border: 1px solid color-mix(in srgb, var(--slide-border) 78%, transparent);
          border-radius: var(--slide-radius-xl);
          background: var(--slide-surface-strong);
          box-shadow: var(--slide-shadow-soft);
        }}

        .header {{
          padding: 38px 42px;
        }}

        .eyebrow {{
          margin: 0 0 16px;
          color: var(--slide-text-secondary);
          font-size: 15px;
          letter-spacing: 0.2em;
          text-transform: uppercase;
        }}

        h1 {{
          margin: 0;
          font-family: var(--slide-font-title);
          font-size: 60px;
          line-height: 1.08;
          letter-spacing: -0.04em;
        }}

        .summary {{
          margin: 18px 0 0;
          max-width: 960px;
          color: var(--slide-text-secondary);
          font-size: 24px;
          line-height: 1.72;
        }}

        .chart-card {{
          padding: 26px 28px;
        }}
        </style>
        """
    ).strip()


def build_table_sfc(*, title: str, summary: str) -> str:
    columns = [
        {"key": "account", "title": "Account", "width": "34%"},
        {"key": "owner", "title": "Owner", "width": "18%"},
        {"key": "status", "title": "Status", "width": "16%"},
        {"key": "nextAction", "title": "Next Action"},
    ]
    rows = [
        {"account": "Northwind Health", "owner": "Alice", "status": "On track", "nextAction": "推进复购提案"},
        {"account": "Blue Harbor", "owner": "Ben", "status": "Watch", "nextAction": "收敛交付风险"},
        {"account": "Nova Components", "owner": "Cindy", "status": "Expand", "nextAction": "锁定预算窗口"},
    ]
    return dedent(
        f"""
        <script setup lang="ts">
        type TableColumn = {{
          key: string
          title: string
          width?: string
        }}

        type TableRow = Record<string, string>

        const columns: TableColumn[] = {format_ts_json(columns)}
        const rows: TableRow[] = {format_ts_json(rows)}
        </script>

        <template>
          <main class="slide-page">
            <section class="header">
              <p class="eyebrow">Account Table</p>
              <h1>{title}</h1>
              <p class="summary">{summary}</p>
            </section>
            <section class="table-card">
              <DataTable :animated="true" :columns="columns" :data="rows" :striped="true" />
            </section>
          </main>
        </template>

        <style scoped>
        .slide-page {{
          width: 1920px;
          height: 1080px;
          overflow: hidden;
          display: grid;
          grid-template-rows: auto 1fr;
          gap: 28px;
          padding: 72px 78px;
          background:
            radial-gradient(circle at top left, var(--slide-secondary-soft) 0%, transparent 34%),
            linear-gradient(180deg, var(--slide-bg) 0%, color-mix(in srgb, var(--slide-surface) 70%, var(--slide-bg) 30%) 100%);
          color: var(--slide-text);
          font-family: var(--slide-font-body);
        }}

        .header,
        .table-card {{
          border: 1px solid color-mix(in srgb, var(--slide-border) 78%, transparent);
          border-radius: var(--slide-radius-xl);
          background: var(--slide-surface-strong);
          box-shadow: var(--slide-shadow-soft);
        }}

        .header {{
          padding: 38px 42px;
        }}

        .table-card {{
          padding: 26px 28px;
        }}

        .eyebrow {{
          margin: 0 0 16px;
          color: var(--slide-text-secondary);
          font-size: 15px;
          letter-spacing: 0.2em;
          text-transform: uppercase;
        }}

        h1 {{
          margin: 0;
          font-family: var(--slide-font-title);
          font-size: 60px;
          line-height: 1.08;
          letter-spacing: -0.04em;
        }}

        .summary {{
          margin: 18px 0 0;
          max-width: 960px;
          color: var(--slide-text-secondary);
          font-size: 24px;
          line-height: 1.72;
        }}
        </style>
        """
    ).strip()


def build_ending_sfc(*, title: str, bullets: list[str]) -> str:
    return dedent(
        f"""
        <script setup lang="ts">
        const bullets: string[] = {format_ts_json(bullets)}
        </script>

        <template>
          <main class="slide-page">
            <section class="ending-card">
              <p class="eyebrow">Next Step</p>
              <h1>{title}</h1>
              <ul class="bullet-list">
                <li v-for="bullet in bullets" :key="bullet">{{{{ bullet }}}}</li>
              </ul>
            </section>
          </main>
        </template>

        <style scoped>
        .slide-page {{
          width: 1920px;
          height: 1080px;
          overflow: hidden;
          display: grid;
          place-items: center;
          padding: 80px;
          background:
            radial-gradient(circle at 84% 18%, var(--slide-accent-soft) 0%, transparent 18%),
            linear-gradient(180deg, var(--slide-bg) 0%, color-mix(in srgb, var(--slide-surface) 70%, var(--slide-bg) 30%) 100%);
          color: var(--slide-text);
          font-family: var(--slide-font-body);
        }}

        .ending-card {{
          width: min(1240px, 100%);
          display: grid;
          gap: 24px;
          padding: 56px 62px;
          border: 1px solid color-mix(in srgb, var(--slide-border) 78%, transparent);
          border-radius: var(--slide-radius-xl);
          background: var(--slide-surface-strong);
          box-shadow: var(--slide-shadow);
        }}

        .eyebrow {{
          margin: 0;
          color: var(--slide-text-secondary);
          font-size: 16px;
          letter-spacing: 0.2em;
          text-transform: uppercase;
        }}

        h1 {{
          margin: 0;
          font-family: var(--slide-font-title);
          font-size: 62px;
          line-height: 1.08;
          letter-spacing: -0.04em;
        }}

        .bullet-list {{
          display: grid;
          gap: 18px;
          margin: 0;
          padding-left: 26px;
          color: var(--slide-text-secondary);
          font-size: 24px;
          line-height: 1.76;
        }}
        </style>
        """
    ).strip()


def test_phase3_main_flow_covers_outline_generation_batch_pages_preview_files_and_versions(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    excel_path = write_excel_file(tmp_path / "sales.xlsx")
    outline = build_outline("季度经营汇报", PHASE3_MAIN_PAGE_SPECS)
    expected_page_codes = responses_for_page_specs(PHASE3_MAIN_PAGE_SPECS)
    factory = install_fake_chat_model_factory(
        monkeypatch,
        response_batches=[
            [FILE_ANALYZER_RESPONSE, PHASE3_MAIN_OUTLINE_RESPONSE],
            expected_page_codes,
        ],
    )

    with TestClient(app) as client:
        project = create_project(client, name="Phase 3 Main Flow Project")
        upload_response = upload_file_via_api(client, project_id=project["id"], file_path=excel_path)
        chat_status_code, chat_headers, chat_events = stream_agent_chat(
            client,
            project_id=project["id"],
            message="请根据这份销售数据生成季度经营汇报大纲，并准备逐页输出。",
        )
        confirm_status_code, confirm_headers, confirm_events = stream_confirm_outline(
            client,
            project_id=project["id"],
        )
        project_detail = get_project_detail(client, project["id"])
        file_list = list_project_files(client, project["id"])
        messages = list_chat_messages(client, project["id"])

    persisted_pages = load_project_pages(session_factory=session_factory, project_id=project["id"])
    combined_event_names = [*(event["event"] for event in chat_events), *(event["event"] for event in confirm_events)]
    confirm_event_names = [event["event"] for event in confirm_events]
    page_complete_events = [event for event in confirm_events if event["event"] == "page_complete"]

    assert upload_response["parse_status"] == "pending"
    assert chat_status_code == 200
    assert confirm_status_code == 200
    assert chat_headers["content-type"].startswith("text/event-stream")
    assert confirm_headers["content-type"].startswith("text/event-stream")
    assert_event_order(combined_event_names, ["outline", "page_generating", "page_complete", "done"])
    assert [event["event"] for event in chat_events].count("outline") == 1
    assert confirm_event_names.count("page_generating") == outline.total_pages
    assert confirm_event_names.count("page_complete") == outline.total_pages
    assert confirm_event_names[-1] == "done"
    assert [event["data"]["page_number"] for event in page_complete_events] == [1, 2, 3, 4, 5]
    assert file_list["files"][0]["original_name"] == "sales.xlsx"
    assert file_list["files"][0]["parse_status"] == "parsed"
    assert project_detail["status"] == "editing"
    assert project_detail["outline"]["title"] == outline.title
    assert [page["title"] for page in project_detail["pages"]] == [page["title"] for page in PHASE3_MAIN_PAGE_SPECS]
    assert len(project_detail["pages"]) == outline.total_pages
    assert len(persisted_pages) == outline.total_pages
    assert all(len(page.versions) == 1 for page in persisted_pages)
    assert all(page.versions[0].version == 1 for page in persisted_pages)
    assert messages["total"] == 3
    assert [message["role"] for message in messages["messages"]] == ["user", "assistant", "assistant"]
    assert [message["message_type"] for message in messages["messages"]] == ["text", "outline", "text"]
    assert messages["messages"][1]["metadata"]["outline"]["total_pages"] == outline.total_pages
    assert "已确认《季度经营汇报》的 5 页大纲。" in messages["messages"][2]["content"]
    assert not any("正在生成第" in message["content"] for message in messages["messages"])
    assert len(factory.instances) == 2
    assert [len(instance.calls) for instance in factory.instances] == [2, outline.total_pages]
    assert factory.remaining_batches == 0

    assert_preview_files_match(settings=local_settings, page_codes=expected_page_codes)


def test_phase3_theme_switch_before_generation_rewrites_preview_theme_and_keeps_pages_writable(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    outline = build_outline(
        "主题切换经营汇报",
        (
            {
                "title": "主题切换封面",
                "type": "cover",
                "content_brief": "封面页",
                "layout": "center-hero",
                "data_refs": [],
                "variant": "cover",
            },
            {
                "title": "执行摘要",
                "type": "keypoints",
                "content_brief": "摘要页",
                "layout": "bullet-grid",
                "data_refs": [],
                "variant": "metrics",
            },
            {
                "title": "业务趋势",
                "type": "data",
                "content_brief": "趋势图",
                "layout": "chart-focus",
                "data_refs": [],
                "variant": "chart",
            },
        ),
    )
    expected_page_codes = responses_for_outline(outline)
    factory = install_fake_chat_model_factory(
        monkeypatch,
        response_batches=[expected_page_codes],
    )

    with TestClient(app) as client:
        project = create_project(client, name="Phase 3 Theme Switch Project")
        themes_response = client.get("/api/themes")
        assert themes_response.status_code == 200
        business_blue = next(
            theme for theme in themes_response.json()["themes"] if theme["id"] == "business-blue"
        )
        update_theme_response = client.put(f"/api/projects/{project['id']}/theme", json=business_blue)
        confirm_status_code, _, confirm_events = stream_confirm_outline(
            client,
            project_id=project["id"],
            outline=outline,
        )
        project_detail = get_project_detail(client, project["id"])

    theme_css = local_settings.preview_theme_file_path.read_text(encoding="utf-8")
    confirm_event_names = [event["event"] for event in confirm_events]

    assert update_theme_response.status_code == 200
    assert confirm_status_code == 200
    assert update_theme_response.json()["theme_config"]["id"] == "business-blue"
    assert project_detail["theme_config"]["id"] == "business-blue"
    assert project_detail["status"] == "editing"
    assert confirm_event_names.count("page_complete") == outline.total_pages
    assert confirm_event_names[-1] == "done"
    assert "theme: business-blue" in theme_css
    assert "--slide-primary: #3b6ea8;" in theme_css
    assert "--slide-bg: #eef4fb;" in theme_css
    assert len(factory.instances) == 1
    assert factory.runtime_configs[0].deliberation_enabled is False
    assert_preview_files_match(settings=local_settings, page_codes=expected_page_codes)


def test_phase3_confirm_outline_controls_page_generator_deliberation_through_runtime_settings(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    outline = build_outline(
        "思辨开关验证",
        (
            {
                "title": "执行摘要",
                "type": "keypoints",
                "content_brief": "验证思辨开关",
                "layout": "bullet-grid",
                "data_refs": [],
                "variant": "metrics",
            },
        ),
    )
    draft_page_code = build_metrics_sfc(
        title="执行摘要",
        lead="先给出经营判断，再进入拆解。",
        score=82,
        progress_items=[
            {"color": "var(--slide-primary)", "label": "营收质量", "value": 84},
            {"color": "var(--slide-accent)", "label": "项目执行", "value": 79},
        ],
    )
    synthesized_page_code = build_metrics_sfc(
        title="执行摘要（思辨版）",
        lead="思辨后将节奏改为结论、风险、动作三层展开。",
        score=86,
        progress_items=[
            {"color": "var(--slide-primary)", "label": "营收质量", "value": 88},
            {"color": "var(--slide-secondary)", "label": "客户续约", "value": 83},
            {"color": "var(--slide-accent)", "label": "交付稳定性", "value": 80},
        ],
    )
    factory = install_fake_chat_model_factory(
        monkeypatch,
        response_batches=[
            [draft_page_code],
            [draft_page_code, "建议把结论顺序从“指标”调整为“结论-风险-动作”。", synthesized_page_code],
        ],
    )

    with TestClient(app) as client:
        project_disabled = create_project(client, name="Phase 3 Deliberation Disabled")
        update_settings(
            client,
            {
                "llm_provider": "openai_compatible",
                "model_name": "phase3-disabled-model",
                "api_base_url": "https://proxy.disabled.example/v1",
                "multi_agent_deliberation_enabled": False,
            },
        )
        disabled_status_code, _, disabled_events = stream_confirm_outline(
            client,
            project_id=project_disabled["id"],
            outline=outline,
        )

        project_enabled = create_project(client, name="Phase 3 Deliberation Enabled")
        update_settings(
            client,
            {
                "llm_provider": "openai",
                "model_name": "phase3-enabled-model",
                "api_base_url": "https://proxy.enabled.example/v1",
                "multi_agent_deliberation_enabled": True,
            },
        )
        enabled_status_code, _, enabled_events = stream_confirm_outline(
            client,
            project_id=project_enabled["id"],
            outline=outline,
        )

    disabled_event_names = [event["event"] for event in disabled_events]
    enabled_event_names = [event["event"] for event in enabled_events]
    enabled_targets = {
        event["data"].get("target")
        for event in enabled_events
        if event["event"].startswith("deliberation_")
    }

    assert disabled_status_code == 200
    assert enabled_status_code == 200
    assert "deliberation_started" not in disabled_event_names
    assert "deliberation_round" not in disabled_event_names
    assert "deliberation_summary" not in disabled_event_names
    assert "deliberation_started" in enabled_event_names
    assert "deliberation_round" in enabled_event_names
    assert "deliberation_summary" in enabled_event_names
    assert_event_order(
        enabled_event_names,
        ["page_generating", "deliberation_started", "deliberation_round", "deliberation_summary", "page_complete", "done"],
    )
    assert enabled_targets == {"page_generator"}
    assert len(factory.instances) == 2
    assert [config.deliberation_enabled for config in factory.runtime_configs] == [False, True]
    assert [config.provider for config in factory.runtime_configs] == [
        LLMProvider.OPENAI_COMPATIBLE,
        LLMProvider.OPENAI,
    ]
    assert [config.model_name for config in factory.runtime_configs] == [
        "phase3-disabled-model",
        "phase3-enabled-model",
    ]
    assert [config.api_base_url for config in factory.runtime_configs] == [
        "https://proxy.disabled.example/v1",
        "https://proxy.enabled.example/v1",
    ]


def test_phase3_page_generator_fallback_still_persists_page_and_preview_artifacts(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    outline = build_outline(
        "思辨回退验证",
        (
            {
                "title": "风险与动作",
                "type": "data",
                "content_brief": "验证回退逻辑",
                "layout": "chart-focus",
                "data_refs": [],
                "variant": "chart",
            },
        ),
    )
    draft_page_code = build_chart_sfc(
        title="风险与动作",
        summary="先输出 Draft 图表页，再模拟 critic 失败。",
        series_name="经营风险指数",
        values=[68, 72, 75, 81],
    )
    factory = install_fake_chat_model_factory(
        monkeypatch,
        response_batches=[[draft_page_code, RuntimeError("critic exploded")]],
    )

    with TestClient(app) as client:
        project = create_project(client, name="Phase 3 Fallback Project")
        update_settings(client, {"multi_agent_deliberation_enabled": True})
        status_code, _, events = stream_confirm_outline(
            client,
            project_id=project["id"],
            outline=outline,
        )
        project_detail = get_project_detail(client, project["id"])

    persisted_pages = load_project_pages(session_factory=session_factory, project_id=project["id"])
    summary_event = next(event for event in events if event["event"] == "deliberation_summary")
    page_complete_event = next(event for event in events if event["event"] == "page_complete")

    assert status_code == 200
    assert project_detail["status"] == "editing"
    assert summary_event["data"]["target"] == "page_generator"
    assert "回退到 Draft 页面" in summary_event["data"]["summary"]
    assert page_complete_event["data"]["page_number"] == 1
    assert page_complete_event["data"]["vue_code"] == draft_page_code
    assert len(persisted_pages) == 1
    assert persisted_pages[0].vue_code == draft_page_code
    assert len(persisted_pages[0].versions) == 1
    assert_preview_files_match(settings=local_settings, page_codes=[draft_page_code])
    assert len(factory.instances) == 1
    assert factory.runtime_configs[0].deliberation_enabled is True


def test_phase3_bulk_generation_smoke_handles_sixteen_pages_stably(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    outline = build_smoke_outline(page_count=16)
    expected_page_codes = responses_for_outline(outline)
    factory = install_fake_chat_model_factory(
        monkeypatch,
        response_batches=[expected_page_codes],
    )

    with TestClient(app) as client:
        project = create_project(client, name="Phase 3 Bulk Smoke Project")
        status_code, _, events = stream_confirm_outline(
            client,
            project_id=project["id"],
            outline=outline,
        )
        project_detail = get_project_detail(client, project["id"])

    event_names = [event["event"] for event in events]

    assert status_code == 200
    assert event_names.count("page_generating") == outline.total_pages
    assert event_names.count("page_complete") == outline.total_pages
    assert event_names[-1] == "done"
    assert project_detail["status"] == "editing"
    assert len(project_detail["pages"]) == outline.total_pages
    assert [page["page_number"] for page in project_detail["pages"]] == list(range(1, outline.total_pages + 1))
    assert len(factory.instances) == 1
    assert len(factory.instances[0].calls) == outline.total_pages
    assert_preview_files_match(settings=local_settings, page_codes=expected_page_codes)


def test_phase3_batch_generation_stops_after_failure_without_marking_later_pages_generated(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_settings = build_local_settings(settings)
    app = build_test_app(settings=local_settings, session_factory=session_factory)
    outline = build_outline(
        "失败保护验证",
        (
            {
                "title": "封面",
                "type": "cover",
                "content_brief": "第一页可以正常生成",
                "layout": "center-hero",
                "data_refs": [],
                "variant": "cover",
            },
            {
                "title": "经营趋势",
                "type": "data",
                "content_brief": "第二页模拟失败",
                "layout": "chart-focus",
                "data_refs": [],
                "variant": "chart",
            },
            {
                "title": "重点账户",
                "type": "data",
                "content_brief": "失败后不应继续",
                "layout": "table-focus",
                "data_refs": [],
                "variant": "table",
            },
            {
                "title": "下一步计划",
                "type": "ending",
                "content_brief": "失败后不应继续",
                "layout": "title-body",
                "data_refs": [],
                "variant": "ending",
            },
        ),
    )
    first_page_code = response_for_outline_page(outline.pages[0])
    factory = install_fake_chat_model_factory(
        monkeypatch,
        response_batches=[[first_page_code, RuntimeError("draft failed"), RuntimeError("repair failed")]],
    )

    with TestClient(app) as client:
        project = create_project(client, name="Phase 3 Failure Guard Project")
        status_code, _, events = stream_confirm_outline(
            client,
            project_id=project["id"],
            outline=outline,
        )
        project_detail = get_project_detail(client, project["id"])

    persisted_pages = load_project_pages(session_factory=session_factory, project_id=project["id"])
    event_names = [event["event"] for event in events]
    error_event = next(event for event in events if event["event"] == "error")
    generated_page_numbers = [event["data"]["page_number"] for event in events if event["event"] == "page_complete"]

    assert status_code == 200
    assert event_names.count("page_generating") == 2
    assert event_names.count("page_complete") == 1
    assert generated_page_numbers == [1]
    assert event_names[-1] == "done"
    assert error_event["data"]["message"].startswith("确认大纲失败：")
    assert project_detail["status"] == "generating"
    assert [page.page_number for page in persisted_pages] == [1]
    assert persisted_pages[0].status.value == "generated"
    assert len(persisted_pages[0].versions) == 1
    assert_preview_files_match(settings=local_settings, page_codes=[first_page_code])
    assert not (local_settings.preview_slides_dir_path / "page-2.vue").exists()
    assert len(factory.instances) == 1
    assert len(factory.instances[0].calls) == 3
