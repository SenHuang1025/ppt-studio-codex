from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.files import get_file_service, router
from app.models.enums import FileParseStatus


@dataclass
class FakeUploadedFile:
    id: str
    parse_status: FileParseStatus
    parsed_content: dict | None


class FakeFileService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def get_parsed_file(self, project_id: str, file_id: str) -> FakeUploadedFile:
        self.calls.append("get")
        if self.calls == ["get"]:
            return FakeUploadedFile(
                id=file_id,
                parse_status=FileParseStatus.PENDING,
                parsed_content=None,
            )

        return FakeUploadedFile(
            id=file_id,
            parse_status=FileParseStatus.PARSED,
            parsed_content={"summary": "parsed", "file_type": "txt"},
        )

    async def parse_file(self, project_id: str, file_id: str, force: bool = False) -> FakeUploadedFile:
        self.calls.append("parse")
        return FakeUploadedFile(
            id=file_id,
            parse_status=FileParseStatus.PARSED,
            parsed_content={"summary": "parsed", "file_type": "txt"},
        )


def test_get_parsed_endpoint_lazy_parses_pending_file() -> None:
    app = FastAPI()
    app.include_router(router)
    fake_service = FakeFileService()
    app.dependency_overrides[get_file_service] = lambda: fake_service

    with TestClient(app) as client:
        response = client.get("/api/projects/project-1/files/file-1/parsed")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "parsed_content": {"summary": "parsed", "file_type": "txt"},
        "status": "parsed",
    }
    assert fake_service.calls == ["get", "parse"]
