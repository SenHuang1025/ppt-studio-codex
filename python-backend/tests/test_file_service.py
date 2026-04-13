from __future__ import annotations

import asyncio
import io

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.models.enums import FileParseStatus
from app.parsers.base import ParseResult
from app.parsers.registry import parser_registry
from app.services import FileParsingError, FileService


class BlockingParser:
    def __init__(self, started: asyncio.Event, release: asyncio.Event):
        self.started = started
        self.release = release

    async def parse(self, file_path: str) -> ParseResult:
        self.started.set()
        await self.release.wait()
        return ParseResult(
            file_type="txt",
            summary="Blocking parse finished.",
            text_content="blocking parser output",
            structured_data={"source": "test"},
            key_points=["blocking parser"],
        )


class FailingParser:
    async def parse(self, file_path: str) -> ParseResult:
        raise RuntimeError("simulated parser failure")


@pytest.mark.asyncio
async def test_parse_file_updates_pending_parsing_and_parsed(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    project_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    monkeypatch.setitem(parser_registry._parsers, "txt", BlockingParser(started, release))

    async with session_factory() as session:
        file_service = FileService(session=session, settings=settings)
        upload_file = UploadFile(filename="notes.txt", file=io.BytesIO(b"Quarterly notes"))
        uploaded_file = await file_service.upload_file(project_id, upload_file)

        assert uploaded_file.parse_status == FileParseStatus.PENDING

        parse_task = asyncio.create_task(file_service.parse_file(project_id, uploaded_file.id))
        await asyncio.wait_for(started.wait(), timeout=5)

        async with session_factory() as observer_session:
            observer_service = FileService(session=observer_session, settings=settings)
            observed_file = await observer_service.get_parsed_file(project_id, uploaded_file.id)
            assert observed_file.parse_status == FileParseStatus.PARSING

        release.set()
        parsed_file = await parse_task

        assert parsed_file.parse_status == FileParseStatus.PARSED
        assert parsed_file.parsed_content is not None
        assert parsed_file.parsed_content["summary"] == "Blocking parse finished."


@pytest.mark.asyncio
async def test_parse_file_marks_failed_when_parser_raises(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    project_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(parser_registry._parsers, "txt", FailingParser())

    async with session_factory() as session:
        file_service = FileService(session=session, settings=settings)
        upload_file = UploadFile(filename="broken.txt", file=io.BytesIO(b"bad content"))
        uploaded_file = await file_service.upload_file(project_id, upload_file)

        with pytest.raises(FileParsingError):
            await file_service.parse_file(project_id, uploaded_file.id)

        failed_file = await file_service.get_parsed_file(project_id, uploaded_file.id)
        assert failed_file.parse_status == FileParseStatus.FAILED
        assert failed_file.parsed_content is not None
        assert failed_file.parsed_content["structured_data"]["error"]["message"] == "simulated parser failure"
