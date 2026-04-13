from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.parsers.base import BaseParser, ParseResult
from app.parsers.utils import (
    decode_bytes,
    describe_json_structure,
    extract_key_points,
    non_empty_lines,
    normalize_file_type,
    summarize_text,
    to_jsonable,
    truncate_text,
    unique_strings,
)


class TextParser(BaseParser):
    async def parse(self, file_path: str) -> ParseResult:
        return await asyncio.to_thread(self._parse_sync, file_path)

    def _parse_sync(self, file_path: str) -> ParseResult:
        path = Path(file_path)
        file_type = normalize_file_type(file_path)
        raw_bytes = path.read_bytes()
        text, encoding = decode_bytes(raw_bytes)

        if file_type == "json":
            return self._parse_json_document(text, encoding)

        return self._parse_text_document(text=text, file_type=file_type, encoding=encoding)

    def _parse_text_document(self, *, text: str, file_type: str, encoding: str) -> ParseResult:
        lines = non_empty_lines(text)
        headings = [
            line.lstrip("#").strip()
            for line in lines
            if file_type == "md" and line.startswith("#")
        ]
        summary_prefix = (
            f"Markdown document with {len(headings)} headings."
            if file_type == "md"
            else f"Text document with {len(lines)} non-empty lines."
        )
        key_points = unique_strings(headings + extract_key_points(text), max_items=5)

        return ParseResult(
            file_type=file_type,
            summary=summarize_text(text, prefix=summary_prefix),
            text_content=text,
            structured_data={
                "encoding": encoding,
                "line_count": len(text.splitlines()),
                "character_count": len(text),
                "headings": headings[:20],
            },
            key_points=key_points,
        )

    def _parse_json_document(self, text: str, encoding: str) -> ParseResult:
        payload = json.loads(text)
        pretty_text = json.dumps(payload, ensure_ascii=False, indent=2)
        top_level_keys = list(payload.keys()) if isinstance(payload, dict) else []
        summary = (
            f"JSON document with {len(top_level_keys)} top-level keys."
            if top_level_keys
            else f"JSON document with top-level type {type(payload).__name__}."
        )
        key_points = self._json_key_points(payload)

        return ParseResult(
            file_type="json",
            summary=summary,
            text_content=pretty_text,
            structured_data={
                "encoding": encoding,
                "top_level_type": type(payload).__name__,
                "top_level_keys": top_level_keys[:20],
                "structure_overview": describe_json_structure(payload),
            },
            key_points=key_points,
        )

    def _json_key_points(self, payload: Any) -> list[str]:
        points: list[str] = []
        if isinstance(payload, dict):
            for key, value in list(payload.items())[:5]:
                value_kind = type(value).__name__
                summary = truncate_text(str(to_jsonable(value)), 120)
                points.append(f"{key}: {value_kind} = {summary}")
        elif isinstance(payload, list):
            points.append(f"Top-level list length: {len(payload)}")
            if payload:
                points.append(f"First item type: {type(payload[0]).__name__}")
        else:
            points.append(f"Top-level value: {truncate_text(str(to_jsonable(payload)), 120)}")

        return unique_strings(points, max_items=5)
