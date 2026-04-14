from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any

from app.agents.file_analyzer import file_analyzer_node
from app.agents.llm import LLMRuntime
from app.agents.orchestrator import direct_reply_node, orchestrator_node
from app.agents.planner import deliberate_plan_node, planner_node
from app.agents.state import ProjectState, create_initial_state


@dataclass(slots=True)
class AgentGraphContext:
    chat_service: Any
    file_service: Any
    project_service: Any
    llm_runtime: LLMRuntime


def build_agent_graph(context: AgentGraphContext) -> Any:
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        return _build_fallback_graph(context, exc)

    workflow = StateGraph(ProjectState)
    workflow.add_node("orchestrate", partial(orchestrator_node, model=context.llm_runtime.chat_model))
    workflow.add_node(
        "analyze_files",
        partial(file_analyzer_node, file_service=context.file_service, model=context.llm_runtime.chat_model),
    )
    workflow.add_node(
        "plan_outline",
        partial(planner_node, model=context.llm_runtime.chat_model, project_service=context.project_service),
    )
    workflow.add_node(
        "deliberate_plan",
        partial(deliberate_plan_node, model=context.llm_runtime.chat_model, project_service=context.project_service),
    )
    workflow.add_node("direct_reply", partial(direct_reply_node, model=context.llm_runtime.chat_model))
    workflow.set_entry_point("orchestrate")

    workflow.add_conditional_edges(
        "orchestrate",
        route_by_intent,
        {
            "analyze": "analyze_files",
            "plan": "plan_outline",
            "chat": "direct_reply",
        },
    )
    workflow.add_conditional_edges(
        "analyze_files",
        should_plan_after_analyze,
        {
            "plan": "plan_outline",
            "wait": END,
        },
    )
    workflow.add_conditional_edges(
        "plan_outline",
        should_deliberate_plan,
        {
            "deliberate": "deliberate_plan",
            "finish": END,
        },
    )
    workflow.add_edge("deliberate_plan", END)
    workflow.add_edge("direct_reply", END)

    return workflow.compile()


async def run_agent_workflow(
    *,
    project_id: str,
    message: str,
    page_number: int | None,
    context: AgentGraphContext,
    sse_callback: Any,
    exclude_history_message_id: str | None = None,
) -> ProjectState:
    project = await context.project_service.get_project_detail(project_id)
    chat_history = await context.chat_service.build_agent_history(
        project_id,
        page_number=page_number,
        exclude_message_id=exclude_history_message_id,
    )
    uploaded_files = await context.file_service.list_files(project_id)
    initial_state = create_initial_state(
        project=project,
        project_id=project_id,
        user_message=message,
        page_number=page_number,
        chat_history=chat_history,
        uploaded_files=uploaded_files,
        settings=context.llm_runtime.settings,
        sse_callback=sse_callback,
    )
    graph = build_agent_graph(context)
    return await graph.ainvoke(initial_state)


def route_by_intent(state: ProjectState) -> str:
    return state.get("route") or "chat"


def should_plan_after_analyze(state: ProjectState) -> str:
    return "plan" if state.get("post_analyze_route") == "plan" else "wait"


def should_deliberate_plan(state: ProjectState) -> str:
    draft_outline = state.get("draft_outline")
    return "deliberate" if state.get("deliberation_enabled") and draft_outline is not None else "finish"


def _build_fallback_graph(context: AgentGraphContext, _exc: Exception) -> Any:
    class _FallbackCompiledGraph:
        async def ainvoke(self, state: ProjectState) -> ProjectState:
            current_state = await orchestrator_node(state, model=context.llm_runtime.chat_model)
            route = route_by_intent(current_state)

            if route == "analyze":
                current_state = await file_analyzer_node(
                    current_state,
                    file_service=context.file_service,
                    model=context.llm_runtime.chat_model,
                )
                if should_plan_after_analyze(current_state) == "plan":
                    current_state = await planner_node(
                        current_state,
                        model=context.llm_runtime.chat_model,
                        project_service=context.project_service,
                    )
                    if should_deliberate_plan(current_state) == "deliberate":
                        current_state = await deliberate_plan_node(
                            current_state,
                            model=context.llm_runtime.chat_model,
                            project_service=context.project_service,
                        )
                return current_state

            if route == "plan":
                current_state = await planner_node(
                    current_state,
                    model=context.llm_runtime.chat_model,
                    project_service=context.project_service,
                )
                if should_deliberate_plan(current_state) == "deliberate":
                    current_state = await deliberate_plan_node(
                        current_state,
                        model=context.llm_runtime.chat_model,
                        project_service=context.project_service,
                    )
                return current_state

            return await direct_reply_node(current_state, model=context.llm_runtime.chat_model)

    return _FallbackCompiledGraph()
