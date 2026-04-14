from __future__ import annotations

import json
from typing import Any


def build_file_analyzer_messages(
    *,
    file_name: str,
    file_type: str,
    parsed_content: dict[str, Any],
) -> list[tuple[str, str]]:
    system_prompt = (
        "你是 PPT 文件分析助手。请基于解析器输出，提炼适合做 PPT 规划的摘要。"
        '只返回 JSON，格式为 {"summary":"...","key_points":["..."]}。'
        "summary 需要面向演示结构设计，key_points 保持 3 到 6 条。"
    )
    user_prompt = (
        f"文件名：{file_name}\n"
        f"文件类型：{file_type}\n"
        f"解析结果：{json.dumps(parsed_content, ensure_ascii=False)}"
    )
    return [("system", system_prompt), ("human", user_prompt)]
