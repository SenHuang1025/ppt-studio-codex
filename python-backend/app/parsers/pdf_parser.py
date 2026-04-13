from __future__ import annotations

import asyncio

import fitz

from app.parsers.base import BaseParser, ParseResult
from app.parsers.utils import normalize_file_type, non_empty_lines, truncate_text, unique_strings


class PDFParser(BaseParser):
    async def parse(self, file_path: str) -> ParseResult:
        return await asyncio.to_thread(self._parse_sync, file_path)

    def _parse_sync(self, file_path: str) -> ParseResult:
        pages: list[dict[str, object]] = []
        text_sections: list[str] = []
        key_points: list[str] = []

        with fitz.open(file_path) as document:
            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text").strip()
                preview = truncate_text(page_text, 240)
                line_count = len(non_empty_lines(page_text))
                pages.append(
                    {
                        "page_number": page_number,
                        "char_count": len(page_text),
                        "line_count": line_count,
                        "preview": preview,
                    }
                )
                text_sections.append(
                    f"Page {page_number}\n{page_text if page_text else '[No extractable text]'}"
                )
                if preview:
                    key_points.append(f"Page {page_number}: {preview}")

        pages_with_text = sum(1 for page in pages if page["char_count"])

        return ParseResult(
            file_type=normalize_file_type(file_path),
            summary=f"PDF document with {len(pages)} pages; extracted text from {pages_with_text} pages.",
            text_content="\n\n".join(text_sections),
            structured_data={
                "page_count": len(pages),
                "pages": pages,
            },
            key_points=unique_strings(key_points, max_items=5),
        )
