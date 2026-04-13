from __future__ import annotations

import asyncio

from PIL import ExifTags, Image

from app.parsers.base import BaseParser, ParseResult
from app.parsers.utils import normalize_file_type, to_jsonable, unique_strings


class ImageParser(BaseParser):
    async def parse(self, file_path: str) -> ParseResult:
        return await asyncio.to_thread(self._parse_sync, file_path)

    def _parse_sync(self, file_path: str) -> ParseResult:
        with Image.open(file_path) as image:
            width, height = image.size
            orientation = self._orientation(width=width, height=height)
            format_name = (image.format or normalize_file_type(file_path) or "image").upper()
            exif_preview = self._extract_exif(image)
            summary = (
                f"{format_name} image with resolution {width}x{height} ({orientation}). "
                "Metadata-only parsing is enabled; multimodal visual description is deferred."
            )

            return ParseResult(
                file_type=normalize_file_type(file_path),
                summary=summary,
                text_content=summary,
                structured_data={
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "mode": image.mode,
                    "orientation": orientation,
                    "description_source": "metadata_only",
                    "exif_preview": exif_preview,
                    "vision_description": None,
                },
                key_points=unique_strings(
                    [
                        f"Resolution: {width}x{height}",
                        f"Format: {format_name}",
                        f"Color mode: {image.mode}",
                        "Description source: metadata_only",
                    ],
                    max_items=5,
                ),
            )

    def _orientation(self, *, width: int, height: int) -> str:
        if width == height:
            return "square"
        return "landscape" if width > height else "portrait"

    def _extract_exif(self, image: Image.Image) -> dict[str, object]:
        raw_exif = image.getexif()
        if not raw_exif:
            return {}

        exif_preview: dict[str, object] = {}
        for key, value in list(raw_exif.items())[:10]:
            tag_name = ExifTags.TAGS.get(key, str(key))
            exif_preview[str(tag_name)] = to_jsonable(value)
        return exif_preview
