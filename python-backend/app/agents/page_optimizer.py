from __future__ import annotations

from typing import Any

from loguru import logger

from app.agents.llm import invoke_model_text_with_retry
from app.agents.page_generator import normalize_vue_sfc_output
from app.agents.prompts.page_optimizer_prompt import (
    build_page_optimizer_change_summary_messages,
    build_page_optimizer_critic_messages,
    build_page_optimizer_draft_messages,
    build_page_optimizer_repair_messages,
    build_page_optimizer_synthesis_messages,
)
from app.agents.state import ProjectState
from app.models.enums import PageStatus
from app.schemas.project import OutlinePageSchema
from app.schemas.theme import ThemeConfig
from app.services.thumbnail_service import ThumbnailService


class PageOptimizationError(RuntimeError):
    """Raised when the page optimizer cannot produce a valid Vue SFC."""


async def optimize_page_code(
    *,
    project: Any,
    page: Any,
    page_plan: OutlinePageSchema | dict[str, Any] | None,
    current_page_code: str,
    user_instruction: str,
    page_chat_history: list[dict[str, Any]],
    theme_config: ThemeConfig | dict[str, Any],
    model: Any,
    deliberation_enabled: bool = False,
    sse_callback: Any | None = None,
) -> tuple[str, str]:
    if not current_page_code.strip():
        raise PageOptimizationError("Current page has no Vue SFC code to optimize.")

    normalized_theme = _normalize_theme(theme_config)
    optimization_context = build_page_optimization_input(
        project=project,
        page=page,
        page_plan=page_plan,
        current_page_code=current_page_code,
        user_instruction=user_instruction,
        page_chat_history=page_chat_history,
        theme_config=normalized_theme,
    )
    page_number = int(optimization_context["page"]["page_number"])
    page_title = str(optimization_context["page"].get("title") or f"第 {page_number} 页")

    if sse_callback is not None:
        await sse_callback(
            "thinking",
            {
                "agent": "page_optimizer",
                "content": f"正在根据修改意见优化第 {page_number} 页《{page_title}》。",
            },
        )
        await sse_callback(
            "page_optimizing",
            {
                "page_number": page_number,
                "title": page_title,
                "status": "optimizing",
            },
        )

    draft_code = await _generate_page_optimization_draft(
        optimization_context=optimization_context,
        model=model,
        sse_callback=sse_callback,
    )
    final_code = draft_code

    if deliberation_enabled and sse_callback is not None:
        await sse_callback(
            "deliberation_started",
            {
                "target": "page_optimizer",
                "rounds": 2,
            },
        )
        await sse_callback(
            "deliberation_round",
            {
                "target": "page_optimizer",
                "role": "draft",
                "content": summarize_optimized_page(
                    page_number=page_number,
                    title=page_title,
                    user_instruction=user_instruction,
                ),
            },
        )

    if deliberation_enabled:
        try:
            critic_feedback = await critique_optimized_page(
                optimization_context=optimization_context,
                draft_page_code=draft_code,
                model=model,
                sse_callback=sse_callback,
            )
            if sse_callback is not None:
                await sse_callback(
                    "deliberation_round",
                    {
                        "target": "page_optimizer",
                        "role": "critic",
                        "content": critic_feedback,
                    },
                )

            final_code = await synthesize_optimized_page(
                optimization_context=optimization_context,
                draft_page_code=draft_code,
                critic_feedback=critic_feedback,
                model=model,
                sse_callback=sse_callback,
            )
            if sse_callback is not None:
                await sse_callback(
                    "deliberation_round",
                    {
                        "target": "page_optimizer",
                        "role": "synthesis",
                        "content": summarize_optimized_page(
                            page_number=page_number,
                            title=page_title,
                            user_instruction=user_instruction,
                        ),
                    },
                )
                await sse_callback(
                    "deliberation_summary",
                    {
                        "target": "page_optimizer",
                        "summary": "思辨完成，已输出最终页面优化代码。",
                    },
                )
        except Exception:
            final_code = draft_code
            if sse_callback is not None:
                await sse_callback(
                    "deliberation_summary",
                    {
                        "target": "page_optimizer",
                        "summary": "思辨子流程失败，已回退到 Draft 优化结果。",
                    },
                )

    change_description = await generate_change_description(
        optimization_context=optimization_context,
        optimized_page_code=final_code,
        model=model,
        fallback_instruction=user_instruction,
    )
    return final_code, change_description


async def page_optimizer_node(
    state: ProjectState,
    *,
    model: Any,
    page_service: Any,
) -> ProjectState:
    project = state.get("project")
    page_number = state.get("page_number")
    if page_number is None:
        raise PageOptimizationError("Page optimization requires a page_number.")

    page = _find_project_page(project=project, page_number=page_number)
    if page is None:
        raise PageOptimizationError(f"Page {page_number} was not found in the current project.")

    current_page_code = str(getattr(page, "vue_code", "") or "")
    page_plan = _find_outline_page(state.get("existing_outline"), page_number=page_number)
    optimized_code, change_description = await optimize_page_code(
        project=project,
        page=page,
        page_plan=page_plan,
        current_page_code=current_page_code,
        user_instruction=state["user_message"],
        page_chat_history=_recent_page_history(state.get("chat_history", []), limit=20),
        theme_config=state.get("global_theme") or {},
        model=model,
        deliberation_enabled=state.get("deliberation_enabled", False),
        sse_callback=state.get("sse_callback"),
    )

    page_service.write_preview_slide(page_number=page_number, vue_code=optimized_code)
    updated_page = await page_service.optimize_existing_page(
        project_id=state["project_id"],
        page_number=page_number,
        vue_code=optimized_code,
        change_description=change_description,
    )
    try:
        await ThumbnailService(settings=page_service.settings).refresh_from_preview(
            project_id=state["project_id"],
            page_numbers=[page_number],
        )
    except Exception:
        logger.exception(
            "Failed to refresh thumbnail for project {} page {}",
            state["project_id"],
            page_number,
        )

    page_payload = {
        "id": getattr(updated_page, "id", None),
        "project_id": getattr(updated_page, "project_id", state["project_id"]),
        "page_number": getattr(updated_page, "page_number", page_number),
        "title": getattr(updated_page, "title", None),
        "page_type": getattr(updated_page, "page_type", None),
        "status": getattr(getattr(updated_page, "status", None), "value", getattr(updated_page, "status", None)),
        "version": getattr(updated_page, "version", None),
        "change_description": change_description,
        "vue_code": optimized_code,
    }
    state["optimized_page"] = page_payload
    state["draft_optimized_page_code"] = optimized_code
    state["current_phase"] = "optimizing"
    state["current_page"] = page_number
    assistant_content = f"已修改第 {page_number} 页：{change_description}"
    state["assistant_message"] = assistant_content
    state["persistable_assistant_message"] = {
        "content": assistant_content,
        "message_type": "text",
        "metadata": {
            "page_number": page_number,
            "change_description": change_description,
            "version": page_payload.get("version"),
        },
        "page_number": page_number,
        "role": "assistant",
    }
    await state["sse_callback"](
        "page_updated",
        {
            "page_number": page_number,
            "title": page_payload.get("title"),
            "status": PageStatus.GENERATED.value,
            "version": page_payload.get("version"),
            "change_description": change_description,
            "vue_code": optimized_code,
        },
    )
    await state["sse_callback"]("assistant_message", {"content": assistant_content, "page_number": page_number})
    return state


async def critique_optimized_page(
    *,
    optimization_context: dict[str, Any],
    draft_page_code: str,
    model: Any,
    sse_callback: Any | None = None,
) -> str:
    return await _invoke_model_with_status(
        model,
        build_page_optimizer_critic_messages(
            optimization_context=optimization_context,
            draft_page_code=draft_page_code,
        ),
        stage_label="正在请求页面优化评审意见...",
        sse_callback=sse_callback,
    )


async def synthesize_optimized_page(
    *,
    optimization_context: dict[str, Any],
    draft_page_code: str,
    critic_feedback: str,
    model: Any,
    sse_callback: Any | None = None,
) -> str:
    return await _generate_validated_optimized_page_code(
        optimization_context=optimization_context,
        model=model,
        primary_messages=build_page_optimizer_synthesis_messages(
            optimization_context=optimization_context,
            draft_page_code=draft_page_code,
            critic_feedback=critic_feedback,
        ),
        sse_callback=sse_callback,
    )


async def generate_change_description(
    *,
    optimization_context: dict[str, Any],
    optimized_page_code: str,
    model: Any,
    fallback_instruction: str,
) -> str:
    try:
        response_text = await invoke_model_text_with_retry(
            model,
            build_page_optimizer_change_summary_messages(
                optimization_context=optimization_context,
                optimized_page_code=optimized_page_code,
            ),
        )
    except Exception:
        response_text = ""

    normalized = _normalize_change_description(response_text)
    if normalized:
        return normalized

    fallback = fallback_instruction.strip()
    if len(fallback) <= 40:
        return fallback or "页面优化"
    return f"{fallback[:37].rstrip()}..."


def build_page_optimization_input(
    *,
    project: Any,
    page: Any,
    page_plan: OutlinePageSchema | dict[str, Any] | None,
    current_page_code: str,
    user_instruction: str,
    page_chat_history: list[dict[str, Any]],
    theme_config: ThemeConfig,
) -> dict[str, Any]:
    page_number = getattr(page, "page_number", None)
    normalized_plan = _normalize_optional_outline_page(page_plan)
    if page_number is None and normalized_plan is not None:
        page_number = normalized_plan.page_number

    return {
        "project": {
            "id": getattr(project, "id", None),
            "name": getattr(project, "name", None),
            "description": getattr(project, "description", None),
        },
        "page": {
            "id": getattr(page, "id", None),
            "page_number": page_number,
            "title": getattr(page, "title", None) or (normalized_plan.title if normalized_plan else None),
            "page_type": getattr(page, "page_type", None) or (normalized_plan.type if normalized_plan else None),
            "version": getattr(page, "version", None),
            "status": getattr(getattr(page, "status", None), "value", getattr(page, "status", None)),
        },
        "page_plan": normalized_plan.model_dump(mode="json") if normalized_plan else None,
        "theme": theme_config.model_dump(mode="json"),
        "user_instruction": user_instruction,
        "page_chat_history": _recent_page_history(page_chat_history, limit=20),
        "current_page_code": current_page_code,
    }


async def _generate_page_optimization_draft(
    *,
    optimization_context: dict[str, Any],
    model: Any,
    sse_callback: Any | None = None,
) -> str:
    return await _generate_validated_optimized_page_code(
        optimization_context=optimization_context,
        model=model,
        primary_messages=build_page_optimizer_draft_messages(optimization_context=optimization_context),
        sse_callback=sse_callback,
    )


async def _generate_validated_optimized_page_code(
    *,
    optimization_context: dict[str, Any],
    model: Any,
    primary_messages: list[tuple[str, str]],
    sse_callback: Any | None = None,
) -> str:
    response_text = ""
    try:
        response_text = await _invoke_model_with_status(
            model,
            primary_messages,
            stage_label="正在请求页面优化代码...",
            sse_callback=sse_callback,
        )
        return normalize_vue_sfc_output(response_text)
    except Exception as initial_error:
        repaired_text = await _invoke_model_with_status(
            model,
            build_page_optimizer_repair_messages(
                optimization_context=optimization_context,
                invalid_output=response_text or "<page optimization failed>",
                validation_error=str(initial_error),
            ),
            stage_label="检测到优化后代码可能无法渲染，正在自动修复一次...",
            sse_callback=sse_callback,
        )
        return normalize_vue_sfc_output(repaired_text)


async def _invoke_model_with_status(
    model: Any,
    messages: list[tuple[str, str]],
    *,
    stage_label: str,
    sse_callback: Any | None = None,
) -> str:
    async def handle_retry(attempt: int, error: Exception) -> None:
        logger.warning("Page optimizer LLM invocation retry attempt {} failed: {}", attempt, error)
        if sse_callback is None:
            return

        await sse_callback(
            "thinking",
            {
                "agent": "page_optimizer",
                "content": f"{stage_label} 第 {attempt + 1} 次尝试中...",
            },
        )

    return await invoke_model_text_with_retry(
        model,
        messages,
        retries=3,
        on_retry=handle_retry,
    )


def summarize_optimized_page(*, page_number: int, title: str, user_instruction: str) -> str:
    instruction = user_instruction.strip()
    if len(instruction) > 42:
        instruction = f"{instruction[:39].rstrip()}..."
    return f"第 {page_number} 页《{title}》已按“{instruction}”生成 Draft 优化结果。"


def _find_project_page(*, project: Any, page_number: int) -> Any | None:
    for page in getattr(project, "pages", None) or []:
        if getattr(page, "page_number", None) == page_number:
            return page
    return None


def _find_outline_page(outline: dict[str, Any] | None, *, page_number: int) -> dict[str, Any] | None:
    if not isinstance(outline, dict):
        return None

    pages = outline.get("pages")
    if not isinstance(pages, list):
        return None

    for page in pages:
        if isinstance(page, dict) and page.get("page_number") == page_number:
            return page
    return None


def _normalize_optional_outline_page(page_plan: OutlinePageSchema | dict[str, Any] | None) -> OutlinePageSchema | None:
    if page_plan is None:
        return None
    if isinstance(page_plan, OutlinePageSchema):
        return page_plan
    return OutlinePageSchema.model_validate(page_plan)


def _normalize_theme(theme_config: ThemeConfig | dict[str, Any]) -> ThemeConfig:
    if isinstance(theme_config, ThemeConfig):
        return theme_config
    return ThemeConfig.model_validate(theme_config)


def _recent_page_history(history: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    if limit < 1:
        return []
    return history[-limit:]


def _normalize_change_description(response_text: str) -> str:
    normalized = response_text.strip().strip("\"'“”‘’")
    if not normalized:
        return ""

    for prefix in ("修改内容：", "变更说明：", "摘要："):
        if normalized.startswith(prefix):
            normalized = normalized.removeprefix(prefix).strip()

    normalized = normalized.replace("\n", " ").strip()
    if len(normalized) <= 40:
        return normalized
    return f"{normalized[:37].rstrip()}..."
