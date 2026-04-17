from __future__ import annotations

import re
from typing import Any

from loguru import logger

from app.agents.llm import LLMRenderValidationError, invoke_model_text_with_retry
from app.agents.prompts.page_generator_prompt import (
    build_page_generator_critic_messages,
    build_page_generator_draft_messages,
    build_page_generator_repair_messages,
    build_page_generator_synthesis_messages,
)
from app.schemas.project import OutlinePageSchema
from app.schemas.theme import ThemeConfig


class PageGenerationError(RuntimeError):
    """Raised when the page generator cannot produce a valid Vue SFC."""


class PageGenerationValidationError(PageGenerationError):
    """Raised when a generated Vue SFC does not satisfy baseline constraints."""


class PageRenderingValidationError(PageGenerationValidationError):
    """Raised when generated Vue SFC is likely to fail at runtime rendering."""


async def generate_page_code(
    *,
    project: Any,
    outline_page: OutlinePageSchema | dict[str, Any],
    parsed_contents: list[dict[str, Any]],
    theme_config: ThemeConfig | dict[str, Any],
    current_page_number: int,
    total_pages: int,
    existing_page_code: str | None,
    model: Any,
    deliberation_enabled: bool = False,
    sse_callback: Any | None = None,
    page_generation_context: dict[str, Any] | None = None,
    emit_page_complete: bool = False,
) -> str:
    normalized_page = _normalize_outline_page(outline_page)
    normalized_theme = _normalize_theme(theme_config)
    generation_context = build_page_generation_input(
        project=project,
        outline_page=normalized_page,
        parsed_contents=parsed_contents,
        theme_config=normalized_theme,
        current_page_number=current_page_number,
        total_pages=total_pages,
        existing_page_code=existing_page_code,
        page_generation_context=page_generation_context,
    )

    if sse_callback is not None:
        await sse_callback(
            "thinking",
            {
                "agent": "page_generator",
                "content": f"正在生成第 {current_page_number}/{total_pages} 页《{normalized_page.title}》。",
            },
        )
        await sse_callback(
            "page_generating",
            {
                "page_number": current_page_number,
                "title": normalized_page.title,
                "status": "generating",
            },
        )

    draft_code = await _generate_page_draft(
        generation_context=generation_context,
        model=model,
        sse_callback=sse_callback,
    )
    final_code = draft_code

    if deliberation_enabled and sse_callback is not None:
        await sse_callback(
            "deliberation_started",
            {
                "target": "page_generator",
                "rounds": 2,
            },
        )
        await sse_callback(
            "deliberation_round",
            {
                "target": "page_generator",
                "role": "draft",
                "content": summarize_page_code(normalized_page=normalized_page, page_code=draft_code),
            },
        )

    if deliberation_enabled:
        try:
            critic_feedback = await critique_page_code(
                generation_context=generation_context,
                draft_page_code=draft_code,
                model=model,
                sse_callback=sse_callback,
            )
            if sse_callback is not None:
                await sse_callback(
                    "deliberation_round",
                    {
                        "target": "page_generator",
                        "role": "critic",
                        "content": critic_feedback,
                    },
                )

            synthesized_code = await synthesize_page_code(
                generation_context=generation_context,
                draft_page_code=draft_code,
                critic_feedback=critic_feedback,
                model=model,
                sse_callback=sse_callback,
            )
            final_code = synthesized_code
            if sse_callback is not None:
                await sse_callback(
                    "deliberation_round",
                    {
                        "target": "page_generator",
                        "role": "synthesis",
                        "content": summarize_page_code(normalized_page=normalized_page, page_code=final_code),
                    },
                )
                await sse_callback(
                    "deliberation_summary",
                    {
                        "target": "page_generator",
                        "summary": "思辨完成，已输出最终单页代码。",
                    },
                )
        except Exception:
            final_code = draft_code
            if sse_callback is not None:
                await sse_callback(
                    "deliberation_summary",
                    {
                        "target": "page_generator",
                        "summary": "思辨子流程失败，已回退到 Draft 页面。",
                    },
                )

    if emit_page_complete and sse_callback is not None:
        await sse_callback(
            "page_complete",
            {
                "page_number": current_page_number,
                "title": normalized_page.title,
                "status": "generated",
                "vue_code": final_code,
            },
        )

    return final_code


async def critique_page_code(
    *,
    generation_context: dict[str, Any],
    draft_page_code: str,
    model: Any,
    sse_callback: Any | None = None,
) -> str:
    return await _invoke_model_with_status(
        model,
        build_page_generator_critic_messages(
            generation_context=generation_context,
            draft_page_code=draft_page_code,
        ),
        stage_label="正在请求页面评审意见...",
        sse_callback=sse_callback,
    )


async def synthesize_page_code(
    *,
    generation_context: dict[str, Any],
    draft_page_code: str,
    critic_feedback: str,
    model: Any,
    sse_callback: Any | None = None,
) -> str:
    return await _generate_validated_page_code(
        generation_context=generation_context,
        model=model,
        primary_messages=build_page_generator_synthesis_messages(
            generation_context=generation_context,
            draft_page_code=draft_page_code,
            critic_feedback=critic_feedback,
        ),
        sse_callback=sse_callback,
    )


def build_page_generation_input(
    *,
    project: Any,
    outline_page: OutlinePageSchema,
    parsed_contents: list[dict[str, Any]],
    theme_config: ThemeConfig,
    current_page_number: int,
    total_pages: int,
    existing_page_code: str | None,
    page_generation_context: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "project": {
            "id": getattr(project, "id", None),
            "name": getattr(project, "name", None),
            "description": getattr(project, "description", None),
            "current_page_number": current_page_number,
            "total_pages": total_pages,
        },
        "page": outline_page.model_dump(mode="json"),
        "theme": theme_config.model_dump(mode="json"),
        "page_generation_context": page_generation_context
        or {
            "selected_sources": parsed_contents[:3],
            "all_source_count": len(parsed_contents),
        },
        "existing_page_code": existing_page_code,
    }


async def _generate_page_draft(
    *,
    generation_context: dict[str, Any],
    model: Any,
    sse_callback: Any | None = None,
) -> str:
    return await _generate_validated_page_code(
        generation_context=generation_context,
        model=model,
        primary_messages=build_page_generator_draft_messages(generation_context=generation_context),
        sse_callback=sse_callback,
    )


async def _generate_validated_page_code(
    *,
    generation_context: dict[str, Any],
    model: Any,
    primary_messages: list[tuple[str, str]],
    sse_callback: Any | None = None,
) -> str:
    response_text = ""
    try:
        response_text = await _invoke_model_with_status(
            model,
            primary_messages,
            stage_label="正在请求页面代码...",
            sse_callback=sse_callback,
        )
        return normalize_vue_sfc_output(response_text)
    except Exception as initial_error:
        repaired_text = await _invoke_model_with_status(
            model,
            build_page_generator_repair_messages(
                generation_context=generation_context,
                invalid_output=response_text or "<page generation failed>",
                validation_error=str(initial_error),
            ),
            stage_label="检测到页面代码可能无法渲染，正在自动修复一次...",
            sse_callback=sse_callback,
        )
        return normalize_vue_sfc_output(repaired_text)


def normalize_vue_sfc_output(raw_output: str) -> str:
    sfc_code = extract_vue_sfc(raw_output)
    validate_vue_sfc(sfc_code)
    validate_runtime_renderability(sfc_code)
    return sfc_code


def extract_vue_sfc(raw_output: str) -> str:
    normalized_output = raw_output.strip()
    if not normalized_output:
        raise PageGenerationValidationError("Model returned an empty page response.")

    fenced_match = re.search(r"```(?:vue|html|typescript|ts)?\s*(.*?)\s*```", normalized_output, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        normalized_output = fenced_match.group(1).strip()

    template_index = normalized_output.find("<template")
    script_index = normalized_output.find("<script")
    valid_starts = [index for index in (template_index, script_index) if index >= 0]

    if not valid_starts:
        raise PageGenerationValidationError("Generated output does not contain a Vue SFC block.")

    start_index = min(valid_starts)

    end_candidates = [
        _find_closing_index(normalized_output, "</style>"),
        _find_closing_index(normalized_output, "</script>"),
        _find_closing_index(normalized_output, "</template>"),
    ]
    end_index = max(end_candidates)

    if end_index <= start_index:
        raise PageGenerationValidationError("Generated output is missing a complete Vue SFC ending tag.")

    return normalized_output[start_index:end_index].strip()


def validate_vue_sfc(vue_code: str) -> None:
    missing_sections: list[str] = []
    if "<template" not in vue_code:
        missing_sections.append("<template>")

    if not re.search(r"<script\s+setup\b[^>]*\blang=(['\"])ts\1", vue_code, flags=re.IGNORECASE):
        missing_sections.append('<script setup lang="ts">')

    if missing_sections:
        raise PageGenerationValidationError(
            f"Generated Vue SFC is missing required sections: {', '.join(missing_sections)}."
        )


def validate_runtime_renderability(vue_code: str) -> None:
    if "{{{" in vue_code or "}}}" in vue_code:
        raise PageRenderingValidationError("Generated Vue SFC contains malformed interpolation syntax.")

    template_open_count = len(re.findall(r"<template\b", vue_code, flags=re.IGNORECASE))
    template_close_count = len(re.findall(r"</template>", vue_code, flags=re.IGNORECASE))
    if template_open_count != template_close_count:
        raise PageRenderingValidationError("Generated Vue SFC template block is not balanced.")

    script_open_count = len(re.findall(r"<script\b", vue_code, flags=re.IGNORECASE))
    script_close_count = len(re.findall(r"</script>", vue_code, flags=re.IGNORECASE))
    if script_open_count != script_close_count:
        raise PageRenderingValidationError("Generated Vue SFC script block is not balanced.")

    # Basic runtime guard against unmatched mustache braces that often break preview rendering.
    if vue_code.count("{{") != vue_code.count("}}"):
        raise PageRenderingValidationError("Generated Vue SFC contains unmatched template expressions.")


async def _invoke_model_with_status(
    model: Any,
    messages: list[tuple[str, str]],
    *,
    stage_label: str,
    sse_callback: Any | None = None,
) -> str:
    async def handle_retry(attempt: int, error: Exception) -> None:
        logger.warning("LLM invocation retry attempt {} failed: {}", attempt, error)
        if sse_callback is None:
            return

        await sse_callback(
            "thinking",
            {
                "agent": "page_generator",
                "content": f"{stage_label} 第 {attempt + 1} 次尝试中...",
            },
        )

    return await invoke_model_text_with_retry(
        model,
        messages,
        retries=3,
        on_retry=handle_retry,
    )


def summarize_page_code(*, normalized_page: OutlinePageSchema, page_code: str) -> str:
    component_names = sorted(
        {
            name
            for name in ("CountUp", "AnimatedChart", "ProgressBar", "IconCard", "DataTable")
            if f"<{name}" in page_code
        }
    )
    component_summary = "、".join(component_names) if component_names else "基础原生布局"
    return (
        f"第 {normalized_page.page_number} 页《{normalized_page.title}》Draft 已生成，"
        f"页面类型为 {normalized_page.type}，主要使用：{component_summary}。"
    )


def _normalize_outline_page(outline_page: OutlinePageSchema | dict[str, Any]) -> OutlinePageSchema:
    if isinstance(outline_page, OutlinePageSchema):
        return outline_page
    return OutlinePageSchema.model_validate(outline_page)


def _normalize_theme(theme_config: ThemeConfig | dict[str, Any]) -> ThemeConfig:
    if isinstance(theme_config, ThemeConfig):
        return theme_config
    return ThemeConfig.model_validate(theme_config)


def _find_closing_index(source: str, closing_tag: str) -> int:
    closing_index = source.rfind(closing_tag)
    if closing_index < 0:
        return -1
    return closing_index + len(closing_tag)
