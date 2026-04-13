from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sse_starlette.sse import AppStatus

from app.api.agent import router
from app.api.files import get_file_service
from app.models.enums import FileParseStatus
from app.services import SSEManager


@dataclass
class FakeUploadedFile:
    id: str
    original_name: str
    parse_status: FileParseStatus
    parsed_content: dict[str, Any] | None = None


class EmptyFileService:
    async def list_files(self, project_id: str) -> list[FakeUploadedFile]:
        return []

    async def parse_file(self, project_id: str, file_id: str) -> FakeUploadedFile:
        raise AssertionError("parse_file should not be called when there are no files")


class BrokenFileService:
    async def list_files(self, project_id: str) -> list[FakeUploadedFile]:
        raise RuntimeError("simulated list failure")

    async def parse_file(self, project_id: str, file_id: str) -> FakeUploadedFile:
        raise AssertionError("parse_file should not be called when listing fails")


class ParsingFileService:
    def __init__(self) -> None:
        self.parse_calls: list[str] = []
        self.files = [
            FakeUploadedFile(
                id="file-1",
                original_name="brief.txt",
                parse_status=FileParseStatus.PENDING,
                parsed_content=None,
            ),
            FakeUploadedFile(
                id="file-2",
                original_name="ready.txt",
                parse_status=FileParseStatus.PARSED,
                parsed_content={"summary": "already parsed"},
            ),
        ]

    async def list_files(self, project_id: str) -> list[FakeUploadedFile]:
        return self.files

    async def parse_file(self, project_id: str, file_id: str) -> FakeUploadedFile:
        self.parse_calls.append(file_id)
        parsed_file = FakeUploadedFile(
            id=file_id,
            original_name="brief.txt",
            parse_status=FileParseStatus.PARSED,
            parsed_content={"summary": "提取到项目简介与目标受众。"},
        )
        self.files[0] = parsed_file
        return parsed_file


def test_agent_chat_api_streams_thinking_assistant_and_done() -> None:
    app = build_test_app()
    fake_service = EmptyFileService()
    app.dependency_overrides[get_file_service] = lambda: fake_service

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/projects/project-1/agent/chat",
            json={"message": "请先帮我检查材料"},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)
    event_names = [event["event"] for event in events]

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert event_names[0] == "thinking"
    assert "assistant_message" in event_names
    assert event_names[-1] == "done"


def test_agent_chat_api_streams_error_and_done_when_processing_fails() -> None:
    app = build_test_app()
    fake_service = BrokenFileService()
    app.dependency_overrides[get_file_service] = lambda: fake_service

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/projects/project-1/agent/chat",
            json={"message": "测试错误路径"},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)

    assert response.status_code == 200
    assert [event["event"] for event in events] == ["thinking", "error", "done"]
    assert "simulated list failure" in str(events[1]["data"]["message"])


def test_agent_chat_api_parses_pending_files_and_emits_file_parsed() -> None:
    app = build_test_app()
    fake_service = ParsingFileService()
    app.dependency_overrides[get_file_service] = lambda: fake_service

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/projects/project-1/agent/chat",
            json={"message": "请开始分析现有文件"},
        ) as response:
            payload = "".join(response.iter_text())

    events = parse_sse_events(payload)
    file_parsed_event = next(event for event in events if event["event"] == "file_parsed")

    assert response.status_code == 200
    assert fake_service.parse_calls == ["file-1"]
    assert file_parsed_event["data"] == {
        "file_id": "file-1",
        "file_name": "brief.txt",
        "summary": "提取到项目简介与目标受众。",
    }
    assert [event["event"] for event in events][-1] == "done"


def parse_sse_events(raw_payload: str) -> list[dict[str, Any]]:
    normalized_payload = raw_payload.replace("\r\n", "\n")
    events: list[dict[str, Any]] = []

    for block in normalized_payload.split("\n\n"):
        stripped_block = block.strip()
        if not stripped_block:
            continue

        event_name = "message"
        data_lines: list[str] = []

        for line in stripped_block.split("\n"):
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())

        payload_text = "\n".join(data_lines)
        data = json.loads(payload_text) if payload_text else {}
        events.append({"event": event_name, "data": data})

    return events


def build_test_app() -> FastAPI:
    AppStatus.should_exit = False
    AppStatus.should_exit_event = None

    app = FastAPI()
    app.state.sse_manager = SSEManager()
    app.include_router(router)
    return app
