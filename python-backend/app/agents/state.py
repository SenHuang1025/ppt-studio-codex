from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal, TypedDict

from pydantic import Field

from app.schemas.base import APIModel
from app.schemas.project import OutlineSchema
from app.schemas.settings import SettingsResponse
from app.schemas.theme import ThemeConfig

AgentRoute = Literal["analyze", "plan", "chat"]
ProjectPhase = Literal["chatting", "analyzing", "planning", "generating"]
SSECallback = Callable[[str, dict[str, Any]], Awaitable[None]]


class RouteDecision(APIModel):
    route: AgentRoute
    reason: str
    followup_route: AgentRoute | None = None
    unsupported_capability: Literal["generate", "optimize"] | None = None


class FileAnalysis(APIModel):
    file_id: str
    file_name: str
    file_type: str
    summary: str
    key_points: list[str] = Field(default_factory=list)
    structured_data: dict[str, Any] = Field(default_factory=dict)


class ProjectState(TypedDict):
    project_id: str
    user_message: str
    page_number: int | None
    chat_history: list[dict[str, Any]]
    uploaded_files: list[Any]
    parsed_contents: list[dict[str, Any]]
    outline: dict[str, Any] | None
    current_phase: ProjectPhase
    current_page: int | None
    deliberation_enabled: bool
    deliberation_target: str | None
    deliberation_trace: list[dict[str, Any]]
    sse_callback: SSECallback
    project: Any | None
    route: AgentRoute | None
    route_decision: dict[str, Any] | None
    assistant_message: str | None
    direct_reply: str | None
    settings: SettingsResponse | None
    analysis_summaries: list[str]
    errors: list[str]
    existing_outline: dict[str, Any] | None
    post_analyze_route: AgentRoute | None
    draft_outline: dict[str, Any] | None
    pages: dict[int, dict[str, Any]]
    global_theme: dict[str, Any] | None
    generated_page: dict[str, Any] | None
    generation_target_page: dict[str, Any] | None
    draft_page_code: str | None
    persistable_assistant_message: dict[str, Any] | None


def create_initial_state(
    *,
    project: Any,
    project_id: str,
    user_message: str,
    page_number: int | None,
    chat_history: list[dict[str, Any]],
    uploaded_files: list[Any],
    settings: SettingsResponse,
    sse_callback: SSECallback,
) -> ProjectState:
    existing_outline = _dump_outline(project.outline)

    return ProjectState(
        project_id=project_id,
        user_message=user_message,
        page_number=page_number,
        chat_history=chat_history,
        uploaded_files=uploaded_files,
        parsed_contents=[],
        outline=existing_outline,
        current_phase="chatting",
        current_page=page_number,
        deliberation_enabled=settings.multi_agent_deliberation_enabled,
        deliberation_target=None,
        deliberation_trace=[],
        sse_callback=sse_callback,
        project=project,
        route=None,
        route_decision=None,
        assistant_message=None,
        direct_reply=None,
        settings=settings,
        analysis_summaries=[],
        errors=[],
        existing_outline=existing_outline,
        post_analyze_route=None,
        draft_outline=None,
        pages={},
        global_theme=_dump_theme(project.theme_config),
        generated_page=None,
        generation_target_page=None,
        draft_page_code=None,
        persistable_assistant_message=None,
    )


def _dump_outline(outline: OutlineSchema | dict[str, Any] | None) -> dict[str, Any] | None:
    if outline is None:
        return None

    if isinstance(outline, OutlineSchema):
        return outline.model_dump(mode="json")

    if isinstance(outline, dict):
        return outline

    return None


def _dump_theme(theme: ThemeConfig | dict[str, Any] | None) -> dict[str, Any] | None:
    if theme is None:
        return None

    if isinstance(theme, ThemeConfig):
        return theme.model_dump(mode="json")

    if isinstance(theme, dict):
        return theme

    return None
