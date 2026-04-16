from __future__ import annotations

import json
from typing import Any


def build_orchestrator_classification_messages(
    *,
    user_message: str,
    has_outline: bool,
    pending_file_count: int,
    chat_history: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    system_prompt = (
        "你是 PPT Studio 的 Orchestrator Agent，只能在 analyze、plan、optimize、chat 之间做路由。"
        "优先遵循现有规则：有待解析文件时优先 analyze；规划或调整大纲走 plan；"
        "明确携带 page_number 的页面修改请求走 optimize；寒暄、问答或缺少页码的页面请求走 chat。"
        "优先关注当前用户消息，最近对话历史只作为补充背景。"
        "只返回 JSON："
        '{"route":"analyze|plan|optimize|chat","reason":"...","followup_route":"plan|null","unsupported_capability":"generate|optimize|null"}。'
    )
    user_prompt = (
        f"用户消息：{user_message}\n"
        f"项目是否已有 outline：{has_outline}\n"
        f"待解析文件数：{pending_file_count}\n"
        f"最近对话历史：{json.dumps(chat_history, ensure_ascii=False)}\n"
        "只输出 JSON，不要解释。"
    )
    return [("system", system_prompt), ("human", user_prompt)]


def build_direct_reply_messages(
    *,
    user_message: str,
    outline: dict[str, Any] | None,
    parsed_contents: list[dict[str, Any]],
    chat_history: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    system_prompt = (
        "你是 PPT Studio 的对话助手。当前支持文件分析、PPT 大纲规划、确认大纲后的页面生成和指定页码的单页优化。"
        "如果用户想优化页面但没有指定当前页，请提示其在预览模式选中具体页面后再发送修改意见。"
        "优先回答当前用户消息，最近对话历史只作为补充背景。"
        "请给出一条简洁、自然、边界清晰的中文回复，不要超过 120 字。"
    )
    user_prompt = (
        f"用户消息：{user_message}\n"
        f"当前是否已有大纲：{bool(outline)}\n"
        f"已整理材料数：{len(parsed_contents)}\n"
        f"最近对话历史：{json.dumps(chat_history, ensure_ascii=False)}"
    )
    return [("system", system_prompt), ("human", user_prompt)]
