from __future__ import annotations

from typing import Any

from loguru import logger

from app.agents.llm import extract_json_payload, invoke_model_text
from app.agents.prompts.file_analyzer_prompt import build_file_analyzer_messages
from app.agents.state import FileAnalysis, ProjectState


async def file_analyzer_node(
    state: ProjectState,
    *,
    file_service: Any,
    model: Any | None = None,
) -> ProjectState:
    await state["sse_callback"](
        "thinking",
        {
            "agent": "file_analyzer",
            "content": "正在整理项目资料，并提炼适合做 PPT 规划的重点。",
        },
    )

    uploaded_files = state.get("uploaded_files") or await file_service.list_files(state["project_id"])
    state["uploaded_files"] = uploaded_files
    parsed_contents: list[dict[str, Any]] = []
    analysis_summaries: list[str] = []

    for uploaded_file in uploaded_files:
        try:
            parsed_file = await _ensure_parsed_file(
                file_service=file_service,
                project_id=state["project_id"],
                uploaded_file=uploaded_file,
            )
        except Exception as exc:
            file_name = _read_attr(uploaded_file, "original_name") or _read_attr(uploaded_file, "file_name") or "未知文件"
            error_message = f"文件 {file_name} 解析失败：{str(exc) or exc.__class__.__name__}"
            state["errors"].append(error_message)
            await state["sse_callback"]("error", {"message": error_message})
            continue

        parsed_content = _read_attr(parsed_file, "parsed_content") or {}
        analysis = await _build_file_analysis(
            uploaded_file=parsed_file,
            parsed_content=parsed_content,
            model=model,
        )
        parsed_contents.append(analysis.model_dump(mode="json"))
        analysis_summaries.append(f"{analysis.file_name}: {analysis.summary}")
        await state["sse_callback"](
            "file_parsed",
            {
                "file_id": analysis.file_id,
                "file_name": analysis.file_name,
                "summary": analysis.summary,
            },
        )

    state["parsed_contents"] = parsed_contents
    state["analysis_summaries"] = analysis_summaries
    state["current_phase"] = "analyzing"
    return state


async def _ensure_parsed_file(*, file_service: Any, project_id: str, uploaded_file: Any) -> Any:
    parse_status = _read_attr(uploaded_file, "parse_status")
    normalized_status = getattr(parse_status, "value", parse_status)
    parsed_content = _read_attr(uploaded_file, "parsed_content")

    if normalized_status == "parsed" and parsed_content is not None:
        return uploaded_file

    return await file_service.parse_file(project_id, _read_attr(uploaded_file, "id"))


async def _build_file_analysis(*, uploaded_file: Any, parsed_content: dict[str, Any], model: Any | None) -> FileAnalysis:
    fallback_summary = _normalize_text(parsed_content.get("summary")) or "已完成文件解析。"
    fallback_key_points = _normalize_string_list(parsed_content.get("key_points"))

    if model is not None:
        try:
            response_text = await invoke_model_text(
                model,
                build_file_analyzer_messages(
                    file_name=_read_attr(uploaded_file, "original_name"),
                    file_type=_read_attr(uploaded_file, "file_type"),
                    parsed_content=parsed_content,
                ),
            )
            llm_payload = extract_json_payload(response_text)
            if isinstance(llm_payload, dict):
                summary = _normalize_text(llm_payload.get("summary")) or fallback_summary
                key_points = _normalize_string_list(llm_payload.get("key_points")) or fallback_key_points
            else:
                summary = fallback_summary
                key_points = fallback_key_points
        except Exception:
            logger.warning(
                "Falling back to parser summary for file {} during planning analysis.",
                _read_attr(uploaded_file, "id"),
            )
            summary = fallback_summary
            key_points = fallback_key_points
    else:
        summary = fallback_summary
        key_points = fallback_key_points

    return FileAnalysis(
        file_id=_read_attr(uploaded_file, "id"),
        file_name=_read_attr(uploaded_file, "original_name"),
        file_type=_read_attr(uploaded_file, "file_type"),
        summary=summary,
        key_points=key_points,
        structured_data=_normalize_structured_data(parsed_content.get("structured_data")),
    )


def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            normalized = item.strip()
            if normalized:
                items.append(normalized)

    return items


def _normalize_structured_data(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_attr(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)
