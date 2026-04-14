from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.agents.llm import extract_json_payload, invoke_model_text
from app.agents.prompts.planner_prompt import (
    build_planner_critic_messages,
    build_planner_draft_messages,
    build_planner_repair_messages,
    build_planner_synthesis_messages,
)
from app.agents.state import ProjectState
from app.schemas.project import OutlinePageSchema, OutlineSchema

ALLOWED_PAGE_TYPES = {
    "cover",
    "toc",
    "data",
    "comparison",
    "timeline",
    "content",
    "keypoints",
    "quote",
    "thankyou",
}

DEFAULT_LAYOUT_BY_TYPE = {
    "cover": "center-hero",
    "toc": "section-list",
    "data": "kpi-grid",
    "comparison": "two-column-compare",
    "timeline": "horizontal-timeline",
    "content": "title-body",
    "keypoints": "bullet-grid",
    "quote": "quote-focus",
    "thankyou": "closing-message",
}


class PlannerOutputError(RuntimeError):
    """Raised when the planner cannot produce a valid outline."""


async def planner_node(
    state: ProjectState,
    *,
    model: Any,
    project_service: Any,
) -> ProjectState:
    await state["sse_callback"](
        "thinking",
        {
            "agent": "planner",
            "content": "正在结合需求和资料，规划 PPT 大纲结构。",
        },
    )

    draft_outline = await generate_outline_draft(state, model=model)

    if state["deliberation_enabled"]:
        state["draft_outline"] = draft_outline.model_dump(mode="json")
        state["current_phase"] = "planning"
        state["deliberation_target"] = "planner"
        return state

    await _persist_and_emit_outline(state, project_service=project_service, outline=draft_outline)
    return state


async def deliberate_plan_node(
    state: ProjectState,
    *,
    model: Any,
    project_service: Any,
) -> ProjectState:
    draft_outline = OutlineSchema.model_validate(state["draft_outline"] or state["outline"])

    await state["sse_callback"](
        "deliberation_started",
        {
            "target": "planner",
            "rounds": 2,
        },
    )

    draft_summary = summarize_outline(draft_outline)
    await state["sse_callback"](
        "deliberation_round",
        {
            "target": "planner",
            "role": "draft",
            "content": draft_summary,
        },
    )
    state["deliberation_trace"].append(
        {
            "target": "planner",
            "role": "draft",
            "content": draft_summary,
        },
    )

    final_outline = draft_outline
    summary_message = "思辨完成，已输出最终大纲。"

    try:
        critic_feedback = await critique_outline(state, draft_outline=draft_outline, model=model)
        await state["sse_callback"](
            "deliberation_round",
            {
                "target": "planner",
                "role": "critic",
                "content": critic_feedback,
            },
        )
        state["deliberation_trace"].append(
            {
                "target": "planner",
                "role": "critic",
                "content": critic_feedback,
            },
        )

        final_outline = await synthesize_outline(
            state,
            draft_outline=draft_outline,
            critic_feedback=critic_feedback,
            model=model,
        )
        synthesis_message = summarize_outline(final_outline)
        await state["sse_callback"](
            "deliberation_round",
            {
                "target": "planner",
                "role": "synthesis",
                "content": synthesis_message,
            },
        )
        state["deliberation_trace"].append(
            {
                "target": "planner",
                "role": "synthesis",
                "content": synthesis_message,
            },
        )
    except Exception:
        summary_message = "思辨子流程失败，已回退到 Draft 大纲。"
        final_outline = draft_outline

    await state["sse_callback"](
        "deliberation_summary",
        {
            "target": "planner",
            "summary": summary_message,
        },
    )
    state["deliberation_trace"].append(
        {
            "target": "planner",
            "role": "summary",
            "content": summary_message,
        },
    )
    await _persist_and_emit_outline(state, project_service=project_service, outline=final_outline)
    return state


async def generate_outline_draft(state: ProjectState, *, model: Any) -> OutlineSchema:
    planning_context = build_planning_context(state)
    response_text = await invoke_model_text(
        model,
        build_planner_draft_messages(planning_context=planning_context),
    )

    try:
        return parse_outline_response(
            raw_output=response_text,
            project=state.get("project"),
            existing_outline=state.get("existing_outline"),
        )
    except Exception as initial_error:
        repaired_text = await invoke_model_text(
            model,
            build_planner_repair_messages(
                planning_context=planning_context,
                invalid_output=response_text,
                validation_error=str(initial_error),
            ),
        )
        return parse_outline_response(
            raw_output=repaired_text,
            project=state.get("project"),
            existing_outline=state.get("existing_outline"),
        )


async def critique_outline(state: ProjectState, *, draft_outline: OutlineSchema, model: Any) -> str:
    return await invoke_model_text(
        model,
        build_planner_critic_messages(
            planning_context=build_planning_context(state),
            draft_outline=draft_outline.model_dump(mode="json"),
        ),
    )


async def synthesize_outline(
    state: ProjectState,
    *,
    draft_outline: OutlineSchema,
    critic_feedback: str,
    model: Any,
) -> OutlineSchema:
    response_text = await invoke_model_text(
        model,
        build_planner_synthesis_messages(
            planning_context=build_planning_context(state),
            draft_outline=draft_outline.model_dump(mode="json"),
            critic_feedback=critic_feedback,
        ),
    )
    return parse_outline_response(
        raw_output=response_text,
        project=state.get("project"),
        existing_outline=draft_outline.model_dump(mode="json"),
    )


def parse_outline_response(
    *,
    raw_output: str,
    project: Any,
    existing_outline: dict[str, Any] | None,
) -> OutlineSchema:
    try:
        payload = extract_json_payload(raw_output)
        normalized = normalize_outline_payload(
            payload=payload,
            project=project,
            existing_outline=existing_outline,
        )
        return OutlineSchema.model_validate(normalized)
    except (ValueError, TypeError, ValidationError) as exc:
        raise PlannerOutputError(str(exc)) from exc


def normalize_outline_payload(
    *,
    payload: Any,
    project: Any,
    existing_outline: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Planner output must be a JSON object.")

    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, list):
        raw_pages = payload.get("slides")
    if not isinstance(raw_pages, list):
        raise ValueError("Planner output must include a pages array.")

    if len(raw_pages) == 0:
        raise ValueError("Planner output must include at least one page.")

    normalized_pages: list[dict[str, Any]] = []
    total_pages = len(raw_pages)

    for index, raw_page in enumerate(raw_pages, start=1):
        if not isinstance(raw_page, dict):
            raise ValueError("Each page entry must be an object.")

        title = _coerce_text(raw_page.get("title")) or f"第 {index} 页"
        page_type = normalize_page_type(
            raw_page.get("type") or raw_page.get("page_type"),
            title=title,
            index=index,
            total_pages=total_pages,
        )
        normalized_pages.append(
            OutlinePageSchema(
                page_number=index,
                title=title,
                type=page_type,
                content_brief=_coerce_text(raw_page.get("content_brief") or raw_page.get("summary")) or title,
                layout=_coerce_text(raw_page.get("layout")) or DEFAULT_LAYOUT_BY_TYPE[page_type],
                data_refs=_coerce_string_list(raw_page.get("data_refs")),
            ).model_dump(mode="json"),
        )

    outline_title = _coerce_text(payload.get("title"))
    if not outline_title:
        outline_title = _coerce_text(existing_outline.get("title") if existing_outline else None)
    if not outline_title:
        outline_title = _coerce_text(getattr(project, "name", None)) or "PPT 大纲"

    theme_suggestion = _coerce_text(payload.get("theme_suggestion"))
    if not theme_suggestion:
        theme_suggestion = _coerce_text(existing_outline.get("theme_suggestion") if existing_outline else None)
    if not theme_suggestion:
        theme_suggestion = "warm-paper"

    return {
        "title": outline_title,
        "total_pages": len(normalized_pages),
        "theme_suggestion": theme_suggestion,
        "pages": normalized_pages,
    }


def normalize_page_type(value: Any, *, title: str, index: int, total_pages: int) -> str:
    normalized_value = _coerce_text(value).lower()
    if normalized_value in ALLOWED_PAGE_TYPES:
        return normalized_value

    normalized_title = title.lower()
    if index == 1:
        return "cover"
    if index == total_pages and any(keyword in normalized_title for keyword in ("thanks", "thank", "谢谢", "致谢")):
        return "thankyou"
    if any(keyword in normalized_title for keyword in ("目录", "提纲", "议程", "agenda", "toc")):
        return "toc"
    if any(keyword in normalized_title for keyword in ("对比", "比较", "comparison")):
        return "comparison"
    if any(keyword in normalized_title for keyword in ("时间", "里程碑", "timeline")):
        return "timeline"
    if any(keyword in normalized_title for keyword in ("数据", "指标", "营收", "data", "kpi")):
        return "data"
    if any(keyword in normalized_title for keyword in ("总结", "要点", "亮点", "key")):
        return "keypoints"
    if any(keyword in normalized_title for keyword in ("引用", "客户声音", "quote")):
        return "quote"
    if index == total_pages:
        return "thankyou"
    return "content"


def build_planning_context(state: ProjectState) -> dict[str, Any]:
    project = state.get("project")
    return {
        "project": {
            "name": getattr(project, "name", None),
            "description": getattr(project, "description", None),
            "status": getattr(getattr(project, "status", None), "value", getattr(project, "status", None)),
        },
        "user_message": state["user_message"],
        "current_page": state.get("current_page"),
        "existing_outline": state.get("existing_outline"),
        "chat_history": state.get("chat_history", []),
        "parsed_contents": state.get("parsed_contents", []),
        "analysis_summaries": state.get("analysis_summaries", []),
    }


def summarize_outline(outline: OutlineSchema) -> str:
    page_titles = "、".join(page.title for page in outline.pages[:4])
    if outline.total_pages > 4:
        page_titles = f"{page_titles} 等"
    return f"草案共 {outline.total_pages} 页，主题为《{outline.title}》，前几页包含：{page_titles}。"


async def _persist_and_emit_outline(state: ProjectState, *, project_service: Any, outline: OutlineSchema) -> None:
    outline_payload = outline.model_dump(mode="json")
    await project_service.save_outline(state["project_id"], outline)
    state["outline"] = outline_payload
    state["draft_outline"] = outline_payload
    state["current_phase"] = "planning"
    state["persistable_assistant_message"] = {
        "content": build_persisted_outline_summary(outline),
        "message_type": "outline",
        "metadata": {"outline": outline_payload},
        "page_number": state.get("page_number"),
        "role": "assistant",
    }
    await state["sse_callback"]("outline", {"outline": outline_payload})


def build_persisted_outline_summary(outline: OutlineSchema) -> str:
    return f"已生成《{outline.title}》共 {outline.total_pages} 页大纲。"


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value:
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                normalized.append(stripped)
    return normalized
