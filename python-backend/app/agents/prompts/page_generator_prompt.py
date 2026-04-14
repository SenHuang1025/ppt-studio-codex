from __future__ import annotations

import json
from typing import Any

PAGE_GENERATOR_COMPONENT_GUIDE = {
    "CountUp": {
        "description": "数字滚动展示",
        "props": ["end:number", "duration?:number", "prefix?:string", "suffix?:string", "decimals?:number"],
    },
    "AnimatedChart": {
        "description": "ECharts 动画图表容器",
        "props": ["option?:EChartsOption", "animationDelay?:number"],
    },
    "ProgressBar": {
        "description": "进度条",
        "props": ["value:number", "color?:string", "label?:string", "animated?:boolean"],
    },
    "IconCard": {
        "description": "图标指标卡",
        "props": ["icon?:string", "value:string|number", "label:string", "trend?:string"],
    },
    "DataTable": {
        "description": "数据表格",
        "props": ["columns:TableColumn[]", "data:Record<string, unknown>[]", "striped?:boolean", "animated?:boolean"],
    },
}

PAGE_TYPE_GUIDANCE = {
    "cover": "以强标题、副标题、日期/项目元信息为主，视觉重心集中，元素控制在 3 到 5 个块内。",
    "toc": "展示 4 到 6 个章节或议程项，清晰体现当前页在整份 PPT 中的位置。",
    "data": "优先 KPI 卡片、图表、表格，结论要直接，避免堆砌长段文字。",
    "comparison": "适合双栏/三栏对照，保证维度一致、差异点突出。",
    "timeline": "按时间顺序组织节点，节点数量建议 4 到 7 个，强调里程碑与结果。",
    "content": "标题 + 主叙述区 + 辅助块，适合说明策略、方法、结论。",
    "keypoints": "以 3 到 6 条要点为主，可辅以图标卡或侧边强调区。",
    "quote": "突出一句核心引用，保留来源、身份、上下文说明。",
    "thankyou": "收束性页面，保留结束语、联系信息或下一步动作，不再堆数据。",
}

CSS_VARIABLE_GUIDE = [
    "--slide-primary",
    "--slide-secondary",
    "--slide-accent",
    "--slide-bg",
    "--slide-surface",
    "--slide-surface-strong",
    "--slide-surface-soft",
    "--slide-text",
    "--slide-text-secondary",
    "--slide-border",
    "--slide-danger",
    "--slide-danger-soft",
    "--slide-neutral-soft",
    "--slide-primary-soft",
    "--slide-secondary-soft",
    "--slide-accent-soft",
    "--slide-grid-line",
    "--slide-font-title",
    "--slide-font-body",
    "--slide-radius-xl",
    "--slide-radius-lg",
    "--slide-radius-md",
    "--slide-shadow",
    "--slide-shadow-soft",
    "--slide-shadow-card",
]


def build_page_generator_draft_messages(*, generation_context: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("system", _build_page_generator_system_prompt()),
        ("human", json.dumps(_build_generation_payload(generation_context), ensure_ascii=False)),
    ]


def build_page_generator_critic_messages(
    *,
    generation_context: dict[str, Any],
    draft_page_code: str,
) -> list[tuple[str, str]]:
    system_prompt = (
        "你是 PPT Studio 的页面评审 Agent。"
        "请审查 Draft Vue SFC 是否满足页面规划，并重点指出以下问题："
        "布局合理性、信息密度、与主题一致性、组件可执行性、是否符合 1920x1080 幻灯片语境。"
        "请输出简洁中文评审意见，不要返回 JSON，不要重写整页代码。"
    )
    user_prompt = (
        f"页面生成上下文：{json.dumps(_build_generation_payload(generation_context), ensure_ascii=False)}\n"
        f"Draft Vue SFC：\n{draft_page_code}"
    )
    return [("system", system_prompt), ("human", user_prompt)]


def build_page_generator_synthesis_messages(
    *,
    generation_context: dict[str, Any],
    draft_page_code: str,
    critic_feedback: str,
) -> list[tuple[str, str]]:
    system_prompt = (
        "你是 PPT Studio 的页面综合 Agent。"
        "请根据页面生成上下文、Draft Vue SFC 和评审意见，输出最终可运行的完整 Vue3 SFC。"
        "必须返回完整代码，不要使用 Markdown 代码块，不要附加说明。"
        "必须使用 <script setup lang=\"ts\">，并保留 1920x1080 根容器。"
    )
    user_prompt = (
        f"页面生成上下文：{json.dumps(_build_generation_payload(generation_context), ensure_ascii=False)}\n"
        f"Draft Vue SFC：\n{draft_page_code}\n"
        f"评审意见：{critic_feedback}"
    )
    return [("system", system_prompt), ("human", user_prompt)]


def build_page_generator_repair_messages(
    *,
    generation_context: dict[str, Any],
    invalid_output: str,
    validation_error: str,
) -> list[tuple[str, str]]:
    system_prompt = (
        "你需要修复一个不合法的 PPT 页面 Vue SFC 输出。"
        "返回结果必须是完整 Vue3 SFC，且必须包含 <template> 与 <script setup lang=\"ts\">。"
        "不要输出 Markdown，不要解释，不要省略样式。"
    )
    user_prompt = (
        f"页面生成上下文：{json.dumps(_build_generation_payload(generation_context), ensure_ascii=False)}\n"
        f"原始输出：\n{invalid_output}\n"
        f"校验错误：{validation_error}"
    )
    return [("system", system_prompt), ("human", user_prompt)]


def _build_page_generator_system_prompt() -> str:
    return (
        "你是 PPT Studio 的 Page Generator Agent，负责把单页 PPT 规划生成成完整可运行的 Vue3 SFC。\n"
        "硬性要求：\n"
        "1. 只输出完整 Vue3 SFC，不要 Markdown 代码块，不要任何解释文字。\n"
        "2. 必须使用 <script setup lang=\"ts\">。\n"
        "3. 根节点必须是 1920x1080 幻灯片画布，建议包含 width: 1920px、height: 1080px、overflow: hidden。\n"
        "4. 不能调用 fetch / axios / XMLHttpRequest / WebSocket，不能请求任何外部 API，数据必须直接内嵌在脚本里。\n"
        "5. 优先使用预装组件，这些组件已经全局注册，不需要 import："
        f"{json.dumps(PAGE_GENERATOR_COMPONENT_GUIDE, ensure_ascii=False)}。\n"
        "6. 若需要图表，可 import type { EChartsOption } from 'echarts'，并把 option 对象直接写在脚本里。\n"
        "7. 样式必须优先使用现有主题变量，不要自造新的全局 CSS 变量。可用变量包括："
        f"{', '.join(CSS_VARIABLE_GUIDE)}。\n"
        "8. 页面应是 PPT 风格而不是后台管理界面；保持结构清晰、视觉层级明确、信息密度适中。\n"
        "9. 默认写 <style scoped>，避免依赖外部文件和路由、store、props、emit。\n"
        "10. 如果页面类型与数据不匹配，优先保留可执行性和叙事清晰度，不要硬塞复杂组件。\n"
        "页面类型指导：\n"
        f"{json.dumps(PAGE_TYPE_GUIDANCE, ensure_ascii=False)}\n"
        "少量参考示例：\n"
        "示例 A：data 页可使用 3 个 IconCard + 1 个 AnimatedChart + 结论文本，形成上概览下分析。\n"
        "示例 B：comparison 页可使用双栏对照卡片，每栏 3 条对比项，底部再给一个总结条。\n"
        "示例 C：timeline 页可使用 4 到 6 个里程碑节点，节点间距一致，避免长段正文。"
    )


def _build_generation_payload(generation_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": generation_context.get("project"),
        "page": generation_context.get("page"),
        "theme": generation_context.get("theme"),
        "page_generation_context": generation_context.get("page_generation_context"),
        "existing_page_code": generation_context.get("existing_page_code"),
        "available_components": PAGE_GENERATOR_COMPONENT_GUIDE,
        "page_type_guidance": PAGE_TYPE_GUIDANCE,
        "css_variables": CSS_VARIABLE_GUIDE,
        "data_shape_hint": {
            "theme": {
                "id": "string",
                "appearance": "light|dark",
                "colors": "theme colors object",
                "fonts": "theme fonts object",
                "borderRadius": "theme radius object",
                "shadows": "theme shadow object",
            },
            "page": {
                "page_number": "int",
                "title": "string",
                "type": "cover|toc|data|comparison|timeline|content|keypoints|quote|thankyou",
                "content_brief": "string",
                "layout": "string",
                "data_refs": ["string"],
            },
            "source_item": {
                "file_id": "string",
                "file_name": "string",
                "file_type": "string",
                "summary": "string",
                "key_points": ["string"],
                "text_excerpt": "string",
                "structured_data": {"any": "json-like data"},
            },
        },
    }
