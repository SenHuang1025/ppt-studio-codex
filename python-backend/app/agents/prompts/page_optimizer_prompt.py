from __future__ import annotations

import json
from typing import Any

from app.agents.prompts.page_generator_prompt import CSS_VARIABLE_GUIDE, PAGE_GENERATOR_COMPONENT_GUIDE


def build_page_optimizer_draft_messages(*, optimization_context: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("system", _build_page_optimizer_system_prompt()),
        ("human", json.dumps(_build_optimization_payload(optimization_context), ensure_ascii=False)),
    ]


def build_page_optimizer_critic_messages(
    *,
    optimization_context: dict[str, Any],
    draft_page_code: str,
) -> list[tuple[str, str]]:
    system_prompt = (
        "你是 PPT Studio 的页面优化评审 Agent。"
        "请审查 Draft Vue SFC 是否准确执行用户修改指令，重点关注："
        "指令理解准确性、改动范围控制、视觉一致性、主题 CSS 变量使用、代码稳定性。"
        "请输出简洁中文评审意见，不要返回 JSON，不要重写整页代码。"
    )
    user_prompt = (
        f"页面优化上下文：{json.dumps(_build_optimization_payload(optimization_context), ensure_ascii=False)}\n"
        f"Draft Vue SFC：\n{draft_page_code}"
    )
    return [("system", system_prompt), ("human", user_prompt)]


def build_page_optimizer_synthesis_messages(
    *,
    optimization_context: dict[str, Any],
    draft_page_code: str,
    critic_feedback: str,
) -> list[tuple[str, str]]:
    system_prompt = (
        "你是 PPT Studio 的页面优化综合 Agent。"
        "请根据页面优化上下文、Draft Vue SFC 和评审意见，输出最终可运行的完整 Vue3 SFC。"
        "必须返回完整代码，不要使用 Markdown 代码块，不要附加说明。"
        "只修改用户要求和评审指出的必要问题，严格保持其余部分不变。"
    )
    user_prompt = (
        f"页面优化上下文：{json.dumps(_build_optimization_payload(optimization_context), ensure_ascii=False)}\n"
        f"Draft Vue SFC：\n{draft_page_code}\n"
        f"评审意见：{critic_feedback}"
    )
    return [("system", system_prompt), ("human", user_prompt)]


def build_page_optimizer_repair_messages(
    *,
    optimization_context: dict[str, Any],
    invalid_output: str,
    validation_error: str,
) -> list[tuple[str, str]]:
    system_prompt = (
        "你需要修复一个不合法的 PPT 页面优化 Vue SFC 输出。"
        "返回结果必须是完整 Vue3 SFC，且必须包含 <template> 与 <script setup lang=\"ts\">。"
        "不要输出 Markdown，不要解释，不要省略样式。"
        "尽量保留原始页面结构，只修复代码完整性和用户要求的修改。"
    )
    user_prompt = (
        f"页面优化上下文：{json.dumps(_build_optimization_payload(optimization_context), ensure_ascii=False)}\n"
        f"原始输出：\n{invalid_output}\n"
        f"校验错误：{validation_error}"
    )
    return [("system", system_prompt), ("human", user_prompt)]


def build_page_optimizer_change_summary_messages(
    *,
    optimization_context: dict[str, Any],
    optimized_page_code: str,
) -> list[tuple[str, str]]:
    system_prompt = (
        "你是 PPT Studio 的页面修改摘要助手。"
        "请基于用户指令和最终 Vue SFC，用一句简洁中文概括本次页面修改。"
        "不要超过 40 个汉字，不要输出 JSON，不要提及代码。"
    )
    user_prompt = (
        f"用户修改指令：{optimization_context.get('user_instruction')}\n"
        f"页面规划信息：{json.dumps(optimization_context.get('page_plan'), ensure_ascii=False)}\n"
        f"最终 Vue SFC：\n{optimized_page_code}"
    )
    return [("system", system_prompt), ("human", user_prompt)]


def _build_page_optimizer_system_prompt() -> str:
    return (
        "你是 PPT Studio 的 Page Optimizer Agent，负责根据用户反馈修改单个 PPT 页面的完整 Vue3 SFC。\n"
        "硬性要求：\n"
        "1. 只输出完整 Vue3 SFC，不要 Markdown 代码块，不要任何解释文字。\n"
        "2. 你会收到当前页完整 Vue SFC、用户修改指令、最近页面对话历史、页面规划信息和全局主题配置。\n"
        "3. 只修改用户明确要求的部分，严格保持其余模板结构、数据、动画、样式命名和业务文案不变。\n"
        "4. 必须理解自然语言指代，例如“这个图表”“左边的卡片”“标题”“背景色”。\n"
        "5. 必须理解模糊视觉指令，例如“好看一点”“大气一些”“更专业”，并将其转化为克制、稳定的视觉优化。\n"
        "6. 必须保留 <script setup lang=\"ts\"> 和 1920x1080 幻灯片根容器语义。\n"
        "7. 不要调用 fetch / axios / XMLHttpRequest / WebSocket，不要请求任何外部 API。\n"
        "8. 样式必须优先沿用现有主题变量，不要把主题色硬编码替换为无关颜色。可用变量包括："
        f"{', '.join(CSS_VARIABLE_GUIDE)}。\n"
        "9. 如果用户要求具体颜色，例如“标题改成红色”，可以使用对应的主题 danger/accent 变量或必要的具体色值，"
        "但不得破坏页面整体主题体系。\n"
        "10. 可以使用预装组件和库，已有全局组件包括："
        f"{json.dumps(PAGE_GENERATOR_COMPONENT_GUIDE, ensure_ascii=False)}。\n"
        "11. 如果当前页面已有 import、数据数组、图表 option 或动画逻辑，除非用户要求，否则不要重写。\n"
        "12. 输出必须是可运行的 Vue SFC，不能输出 diff、补丁、说明或省略号。"
    )


def _build_optimization_payload(optimization_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": optimization_context.get("project"),
        "page": optimization_context.get("page"),
        "page_plan": optimization_context.get("page_plan"),
        "theme": optimization_context.get("theme"),
        "user_instruction": optimization_context.get("user_instruction"),
        "page_chat_history": optimization_context.get("page_chat_history"),
        "current_page_code": optimization_context.get("current_page_code"),
        "available_components": PAGE_GENERATOR_COMPONENT_GUIDE,
        "css_variables": CSS_VARIABLE_GUIDE,
    }
