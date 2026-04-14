from __future__ import annotations

import json
from typing import Any


def build_planner_draft_messages(*, planning_context: dict[str, Any]) -> list[tuple[str, str]]:
    system_prompt = (
        "你是专业的 PPT 内容策划师。请根据用户目标、已有资料和当前 outline 上下文，输出完整的大纲 JSON。"
        "优先关注当前用户消息和最近对话历史，较早历史仅作补充背景。"
        "页面类型只能使用：cover、toc、data、comparison、timeline、content、keypoints、quote、thankyou。"
        "每页都必须包含 page_number、title、type、content_brief、layout、data_refs。"
        "total_pages 必须等于 pages 数量，页码从 1 开始连续。"
        "只返回 JSON，不要使用 Markdown 代码块，不要附加解释。"
    )
    user_prompt = json.dumps(planning_context, ensure_ascii=False)
    return [("system", system_prompt), ("human", user_prompt)]


def build_planner_repair_messages(
    *,
    planning_context: dict[str, Any],
    invalid_output: str,
    validation_error: str,
) -> list[tuple[str, str]]:
    system_prompt = (
        "你需要修复一个不合法的 PPT outline JSON。"
        "优先保持当前用户需求和最近对话上下文的一致性。"
        "输出仍然必须满足同样的结构约束，并且只能返回 JSON。"
    )
    user_prompt = (
        f"规划上下文：{json.dumps(planning_context, ensure_ascii=False)}\n"
        f"原始输出：{invalid_output}\n"
        f"校验错误：{validation_error}"
    )
    return [("system", system_prompt), ("human", user_prompt)]


def build_planner_critic_messages(
    *,
    planning_context: dict[str, Any],
    draft_outline: dict[str, Any],
) -> list[tuple[str, str]]:
    system_prompt = (
        "你是 PPT 大纲评审员。请从叙事结构、完整性、数据使用合理性三个角度提出批评和改进建议。"
        "请结合最近对话历史理解用户追加要求。"
        "请输出一段简洁中文文本，不要返回 JSON。"
    )
    user_prompt = (
        f"规划上下文：{json.dumps(planning_context, ensure_ascii=False)}\n"
        f"Draft 大纲：{json.dumps(draft_outline, ensure_ascii=False)}"
    )
    return [("system", system_prompt), ("human", user_prompt)]


def build_planner_synthesis_messages(
    *,
    planning_context: dict[str, Any],
    draft_outline: dict[str, Any],
    critic_feedback: str,
) -> list[tuple[str, str]]:
    system_prompt = (
        "你是 PPT 大纲综合 Agent。请结合 Draft 与评审意见，输出最终 outline JSON。"
        "请兼顾最近对话历史里的追加要求。"
        "结果必须满足页面类型、页码连续性和字段完整性要求。"
        "只返回 JSON。"
    )
    user_prompt = (
        f"规划上下文：{json.dumps(planning_context, ensure_ascii=False)}\n"
        f"Draft 大纲：{json.dumps(draft_outline, ensure_ascii=False)}\n"
        f"评审意见：{critic_feedback}"
    )
    return [("system", system_prompt), ("human", user_prompt)]
