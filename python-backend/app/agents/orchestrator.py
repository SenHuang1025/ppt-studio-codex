from __future__ import annotations

from typing import Any

from app.agents.llm import extract_json_payload, invoke_model_text
from app.agents.prompts.orchestrator_prompt import (
    build_direct_reply_messages,
    build_orchestrator_classification_messages,
)
from app.agents.state import ProjectState, RouteDecision

PLANNING_KEYWORDS = (
    "ppt",
    "PPT",
    "演示",
    "汇报",
    "大纲",
    "提纲",
    "目录",
    "页",
    "结构",
    "规划",
    "制作",
    "整理成",
)
OUTLINE_ADJUSTMENT_KEYWORDS = (
    "调整",
    "修改",
    "优化结构",
    "重排",
    "增删",
    "删掉",
    "新增",
    "改成",
    "合并",
)
GENERATE_PAGE_KEYWORDS = (
    "生成页面",
    "直接生成",
    "开始生成",
    "做页面",
    "出页面",
    "生成第",
    "单页",
)
OPTIMIZE_PAGE_KEYWORDS = (
    "优化页面",
    "修改第",
    "改第",
    "当前页",
    "这一页",
    "这页",
    "本页",
    "标题",
    "背景色",
    "好看一点",
    "大气一些",
    "更专业",
)
GREETING_KEYWORDS = (
    "你好",
    "您好",
    "hi",
    "hello",
    "在吗",
    "你是谁",
    "能做什么",
)


async def determine_route(state: ProjectState, *, model: Any | None = None) -> RouteDecision:
    user_message = state["user_message"].strip()
    has_outline = bool(state.get("existing_outline"))
    has_pending_files = _has_pending_files(state.get("uploaded_files", []))

    if state.get("page_number") is not None and _has_existing_page(state, page_number=int(state["page_number"])):
        return RouteDecision(
            route="optimize",
            reason="请求携带 page_number 且页面已存在，进入单页优化。",
        )

    if has_pending_files:
        return RouteDecision(
            route="analyze",
            reason="项目中存在待解析或解析失败的文件，优先进入文件分析。",
            followup_route="plan" if _needs_planning(user_message, has_outline=has_outline) else None,
        )

    if _requests_unsupported_generation(user_message):
        return RouteDecision(
            route="chat",
            reason="当前阶段暂不支持页面生成能力，转为边界说明。",
            unsupported_capability="generate",
        )

    if _requests_unsupported_optimization(user_message):
        if _has_any_existing_page(state):
            return RouteDecision(
                route="chat",
                reason="用户请求页面优化，但没有提供明确 page_number。",
            )
        return RouteDecision(
            route="chat",
            reason="当前项目还没有可优化页面。",
            unsupported_capability="optimize",
        )

    if _needs_planning(user_message, has_outline=has_outline):
        return RouteDecision(
            route="plan",
            reason="用户正在请求创建或调整 PPT 大纲。",
        )

    if _is_general_chat(user_message):
        return RouteDecision(
            route="chat",
            reason="消息属于寒暄、问答或能力询问，直接回复即可。",
        )

    llm_decision = await _maybe_classify_with_llm(
        user_message=user_message,
        has_outline=has_outline,
        model=model,
        pending_file_count=0,
        chat_history=state.get("chat_history", []),
    )
    if llm_decision is not None:
        return llm_decision

    return RouteDecision(
        route="chat",
        reason="当前消息不满足规划规则，采用直接回复。",
    )


async def orchestrator_node(state: ProjectState, *, model: Any | None = None) -> ProjectState:
    await state["sse_callback"](
        "thinking",
        {
            "agent": "orchestrator",
            "content": "正在判断这条消息应该走文件分析、规划，还是直接回复。",
        },
    )

    decision = await determine_route(state, model=model)
    state["route"] = decision.route
    state["route_decision"] = decision.model_dump(mode="json")
    state["post_analyze_route"] = decision.followup_route
    state["current_phase"] = (
        "analyzing"
        if decision.route == "analyze"
        else "planning" if decision.route == "plan" else "optimizing" if decision.route == "optimize" else "chatting"
    )
    return state


async def direct_reply_node(state: ProjectState, *, model: Any | None = None) -> ProjectState:
    await state["sse_callback"](
        "thinking",
        {
            "agent": "assistant",
            "content": "正在整理一条当前阶段可执行的回复。",
        },
    )

    reply = await build_direct_reply(state, model=model)
    state["assistant_message"] = reply
    state["direct_reply"] = reply
    state["persistable_assistant_message"] = {
        "content": reply,
        "message_type": "text",
        "metadata": None,
        "page_number": state.get("page_number"),
        "role": "assistant",
    }
    await state["sse_callback"]("assistant_message", {"content": reply})
    return state


async def build_direct_reply(state: ProjectState, *, model: Any | None = None) -> str:
    user_message = state["user_message"].strip()

    if _requests_unsupported_generation(user_message):
        return "可以生成页面，但请先确认大纲，或使用单页生成入口指定要生成的页码。"

    if _requests_unsupported_optimization(user_message):
        return "可以优化单页，请先切换到预览中的具体页面后再发送修改意见。"

    if model is None:
        return _build_fallback_direct_reply(state)

    try:
        response_text = await invoke_model_text(
            model,
            build_direct_reply_messages(
                user_message=user_message,
                outline=state.get("existing_outline"),
                parsed_contents=state.get("parsed_contents", []),
                chat_history=state.get("chat_history", []),
            ),
        )
    except Exception:
        return _build_fallback_direct_reply(state)

    normalized = response_text.strip()
    return normalized or _build_fallback_direct_reply(state)


def _build_fallback_direct_reply(state: ProjectState) -> str:
    if state.get("existing_outline"):
        return "我现在可以继续帮你调整这份大纲。直接告诉我想增删哪些章节、页数或叙事顺序。"

    if state.get("uploaded_files"):
        return "我已经拿到项目资料。你可以直接告诉我这份 PPT 的主题、受众和目标，我会继续规划大纲。"

    return "当前阶段我可以先帮你分析资料并规划 PPT 大纲。你可以先上传文件，或直接描述主题、受众和汇报目标。"


async def _maybe_classify_with_llm(
    *,
    user_message: str,
    has_outline: bool,
    chat_history: list[dict[str, Any]],
    model: Any | None,
    pending_file_count: int,
) -> RouteDecision | None:
    if model is None:
        return None

    try:
        response_text = await invoke_model_text(
            model,
            build_orchestrator_classification_messages(
                user_message=user_message,
                has_outline=has_outline,
                pending_file_count=pending_file_count,
                chat_history=chat_history,
            ),
        )
        return RouteDecision.model_validate(extract_json_payload(response_text))
    except Exception:
        return None


def _needs_planning(message: str, *, has_outline: bool) -> bool:
    if _contains_keyword(message, PLANNING_KEYWORDS):
        return True

    return has_outline and _contains_keyword(message, OUTLINE_ADJUSTMENT_KEYWORDS)


def _is_general_chat(message: str) -> bool:
    return _contains_keyword(message, GREETING_KEYWORDS) or message.endswith("?") or message.endswith("？")


def _requests_unsupported_generation(message: str) -> bool:
    return _contains_keyword(message, GENERATE_PAGE_KEYWORDS)


def _requests_unsupported_optimization(message: str) -> bool:
    return _contains_keyword(message, OPTIMIZE_PAGE_KEYWORDS)


def _contains_keyword(message: str, keywords: tuple[str, ...]) -> bool:
    normalized_message = message.strip()
    return any(keyword in normalized_message for keyword in keywords)


def _has_pending_files(files: list[Any]) -> bool:
    for uploaded_file in files:
        parse_status = _read_attr(uploaded_file, "parse_status")
        parsed_content = _read_attr(uploaded_file, "parsed_content")
        normalized_status = getattr(parse_status, "value", parse_status)

        if normalized_status in {"pending", "failed"}:
            return True
        if normalized_status == "parsed" and parsed_content is None:
            return True

    return False


def _has_existing_page(state: ProjectState, *, page_number: int) -> bool:
    project = state.get("project")
    for page in getattr(project, "pages", None) or []:
        if getattr(page, "page_number", None) == page_number and getattr(page, "vue_code", None):
            return True
    return False


def _has_any_existing_page(state: ProjectState) -> bool:
    project = state.get("project")
    return any(bool(getattr(page, "vue_code", None)) for page in getattr(project, "pages", None) or [])


def _read_attr(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)
