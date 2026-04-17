from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.services.theme_service import ThemeService
from app.services.thumbnail_service import (
    THUMBNAIL_HEIGHT,
    THUMBNAIL_WIDTH,
    ThumbnailPageSnapshot,
    ThumbnailProjectSnapshot,
    ThumbnailService,
)

VALID_SFC = """
<template>
  <main style="width: 1920px; height: 1080px;">Thumbnail Test</main>
</template>
""".strip()


@pytest.mark.asyncio
async def test_thumbnail_service_captures_resizes_and_cleans_stale_files(settings, monkeypatch) -> None:
    service = ThumbnailService(settings=settings)
    project_id = "project-thumbnail-test"
    thumbnail_dir = settings.project_dir(project_id) / "thumbnails"
    thumbnail_dir.mkdir(parents=True)
    stale_thumbnail = thumbnail_dir / "page-9.png"
    stale_thumbnail.write_bytes(b"stale")

    async def fake_capture_slide_images(*, page_numbers, capture_dir, before_capture=None, file_name_resolver=None):
        if before_capture is not None:
            result = before_capture()
            if hasattr(result, "__await__"):
                await result

        capture_dir.mkdir(parents=True, exist_ok=True)
        captured_paths: list[Path] = []
        for page_number in page_numbers:
            image_path = capture_dir / file_name_resolver(page_number)
            Image.new("RGB", (1920, 1080), color=(page_number, 64, 128)).save(image_path)
            captured_paths.append(image_path)
        return captured_paths

    monkeypatch.setattr(service.capture_service, "capture_slide_images", fake_capture_slide_images)

    snapshot = ThumbnailProjectSnapshot(
        project_id=project_id,
        theme=ThemeService(settings=settings).resolve_theme(None),
        pages=(
            ThumbnailPageSnapshot(page_number=1, vue_code=VALID_SFC),
            ThumbnailPageSnapshot(page_number=2, vue_code=VALID_SFC.replace("Test", "Second")),
        ),
    )

    captured_paths = await service.ensure_project_thumbnails(snapshot=snapshot, page_numbers=[1])

    assert captured_paths == [(thumbnail_dir / "page-1.png").resolve()]
    assert not stale_thumbnail.exists()
    assert (settings.preview_slides_dir_path / "page-1.vue").read_text(encoding="utf-8") == VALID_SFC
    assert (settings.preview_slides_dir_path / "page-2.vue").read_text(encoding="utf-8") == VALID_SFC.replace("Test", "Second")

    with Image.open(thumbnail_dir / "page-1.png") as thumbnail:
        assert thumbnail.size == (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT)
