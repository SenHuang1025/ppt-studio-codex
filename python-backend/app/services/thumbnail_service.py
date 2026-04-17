from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable, Sequence

from loguru import logger
from PIL import Image

from app.config import Settings
from app.schemas import ThemeConfig
from app.services.preview_capture_service import (
    PreviewCaptureDependencyError,
    PreviewCaptureRenderError,
    PreviewCaptureService,
)
from app.services.theme_service import ThemeService

THUMBNAIL_WIDTH = 384
THUMBNAIL_HEIGHT = 216


class ThumbnailServiceError(Exception):
    """Base exception for thumbnail generation failures."""


class ThumbnailNotFoundError(ThumbnailServiceError):
    def __init__(self, project_id: str, page_number: int):
        super().__init__(f"Thumbnail for page {page_number} in project '{project_id}' was not found.")
        self.project_id = project_id
        self.page_number = page_number


class ThumbnailDependencyError(ThumbnailServiceError):
    """Raised when thumbnail runtime dependencies are unavailable."""


class ThumbnailRenderError(ThumbnailServiceError):
    """Raised when preview rendering or thumbnail image processing fails."""


@dataclass(frozen=True, slots=True)
class ThumbnailPageSnapshot:
    page_number: int
    vue_code: str


@dataclass(frozen=True, slots=True)
class ThumbnailProjectSnapshot:
    project_id: str
    theme: ThemeConfig
    pages: tuple[ThumbnailPageSnapshot, ...]


class ThumbnailService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.theme_service = ThemeService(settings=settings)
        self.capture_service = PreviewCaptureService(preview_base_url=settings.preview_base_url)
        self._background_tasks: set[asyncio.Task[None]] = set()

    async def ensure_project_thumbnails(
        self,
        *,
        snapshot: ThumbnailProjectSnapshot,
        page_numbers: Sequence[int] | None = None,
        cleanup_stale: bool = True,
    ) -> list[Path]:
        normalized_target_page_numbers = self._normalize_page_numbers(
            page_numbers if page_numbers is not None else [page.page_number for page in snapshot.pages]
        )
        snapshot_page_numbers = self._normalize_page_numbers(page.page_number for page in snapshot.pages)
        valid_target_page_numbers = [
            page_number for page_number in normalized_target_page_numbers if page_number in set(snapshot_page_numbers)
        ]

        if cleanup_stale:
            self._remove_stale_thumbnails(project_id=snapshot.project_id, expected_page_numbers=snapshot_page_numbers)

        if not valid_target_page_numbers:
            return []

        try:
            captured_paths = await self.capture_service.capture_slide_images(
                page_numbers=valid_target_page_numbers,
                capture_dir=self._thumbnail_dir(snapshot.project_id),
                before_capture=lambda: asyncio.to_thread(self._sync_preview_snapshot, snapshot),
                file_name_resolver=lambda page_number: self._thumbnail_file_name(page_number),
            )
            await asyncio.to_thread(self._resize_images, captured_paths)
            return captured_paths
        except PreviewCaptureDependencyError as exc:
            raise ThumbnailDependencyError(str(exc)) from exc
        except PreviewCaptureRenderError as exc:
            raise ThumbnailRenderError(str(exc)) from exc
        except OSError as exc:
            raise ThumbnailRenderError(f"缩略图写入失败：{exc}") from exc

    async def refresh_from_preview(
        self,
        *,
        project_id: str,
        page_numbers: Sequence[int],
        expected_page_numbers: Sequence[int] | None = None,
    ) -> list[Path]:
        normalized_page_numbers = self._normalize_page_numbers(page_numbers)
        normalized_expected_page_numbers = (
            self._normalize_page_numbers(expected_page_numbers)
            if expected_page_numbers is not None
            else None
        )

        if normalized_expected_page_numbers is not None:
            self._remove_stale_thumbnails(
                project_id=project_id,
                expected_page_numbers=normalized_expected_page_numbers,
            )

        if not normalized_page_numbers:
            return []

        try:
            captured_paths = await self.capture_service.capture_slide_images(
                page_numbers=normalized_page_numbers,
                capture_dir=self._thumbnail_dir(project_id),
                file_name_resolver=lambda page_number: self._thumbnail_file_name(page_number),
            )
            await asyncio.to_thread(self._resize_images, captured_paths)
            return captured_paths
        except PreviewCaptureDependencyError as exc:
            raise ThumbnailDependencyError(str(exc)) from exc
        except PreviewCaptureRenderError as exc:
            raise ThumbnailRenderError(str(exc)) from exc
        except OSError as exc:
            raise ThumbnailRenderError(f"缩略图写入失败：{exc}") from exc

    def schedule_refresh_from_preview(
        self,
        *,
        project_id: str,
        page_numbers: Sequence[int],
        expected_page_numbers: Sequence[int] | None = None,
    ) -> None:
        normalized_page_numbers = self._normalize_page_numbers(page_numbers)
        normalized_expected_page_numbers = (
            self._normalize_page_numbers(expected_page_numbers)
            if expected_page_numbers is not None
            else None
        )
        if not normalized_page_numbers and normalized_expected_page_numbers is None:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        task = loop.create_task(
            self._run_scheduled_refresh(
                project_id=project_id,
                page_numbers=tuple(normalized_page_numbers),
                expected_page_numbers=tuple(normalized_expected_page_numbers) if normalized_expected_page_numbers is not None else None,
            )
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._finalize_background_task)

    def get_thumbnail_path(self, *, project_id: str, page_number: int) -> Path:
        return (self._thumbnail_dir(project_id) / self._thumbnail_file_name(page_number)).resolve()

    def require_thumbnail_path(self, *, project_id: str, page_number: int) -> Path:
        thumbnail_path = self.get_thumbnail_path(project_id=project_id, page_number=page_number)
        if not thumbnail_path.exists():
            raise ThumbnailNotFoundError(project_id, page_number)
        return thumbnail_path

    async def _run_scheduled_refresh(
        self,
        *,
        project_id: str,
        page_numbers: tuple[int, ...],
        expected_page_numbers: tuple[int, ...] | None,
    ) -> None:
        try:
            await self.refresh_from_preview(
                project_id=project_id,
                page_numbers=page_numbers,
                expected_page_numbers=expected_page_numbers,
            )
        except Exception:
            logger.exception(
                "Background thumbnail refresh failed for project {} pages {}",
                project_id,
                list(page_numbers),
            )

    def _finalize_background_task(self, task: asyncio.Task[None]) -> None:
        self._background_tasks.discard(task)
        if task.cancelled():
            return
        try:
            task.result()
        except Exception:
            logger.exception("Thumbnail background task failed unexpectedly.")

    def _sync_preview_snapshot(self, snapshot: ThumbnailProjectSnapshot) -> None:
        self.theme_service.write_preview_theme(snapshot.theme)
        self._sync_preview_slides(snapshot)

    def _sync_preview_slides(self, snapshot: ThumbnailProjectSnapshot) -> None:
        slides_dir = self.settings.preview_slides_dir_path.resolve()
        slides_dir.mkdir(parents=True, exist_ok=True)
        expected_page_numbers = {page.page_number for page in snapshot.pages}

        for page in snapshot.pages:
            target_path = (slides_dir / f"page-{page.page_number}.vue").resolve()
            if not target_path.is_relative_to(slides_dir):
                raise ThumbnailRenderError(f"Unsafe preview slide path resolved: {target_path}")
            target_path.write_text(page.vue_code, encoding="utf-8")

        for path in slides_dir.glob("page-*.vue"):
            page_number = self._parse_page_number(path)
            if page_number is None or page_number not in expected_page_numbers:
                path.unlink(missing_ok=True)

    def _thumbnail_dir(self, project_id: str) -> Path:
        project_dir = self.settings.project_dir(project_id).resolve()
        thumbnail_dir = (project_dir / "thumbnails").resolve()

        if not thumbnail_dir.is_relative_to(project_dir):
            raise ThumbnailRenderError(f"Unsafe thumbnail directory resolved for project '{project_id}'.")

        thumbnail_dir.mkdir(parents=True, exist_ok=True)
        return thumbnail_dir

    def _thumbnail_file_name(self, page_number: int) -> str:
        return f"page-{page_number}.png"

    def _remove_stale_thumbnails(self, *, project_id: str, expected_page_numbers: Sequence[int]) -> None:
        thumbnail_dir = self._thumbnail_dir(project_id)
        expected = set(self._normalize_page_numbers(expected_page_numbers))

        for path in thumbnail_dir.glob("page-*.png"):
            page_number = self._parse_page_number(path)
            if page_number is None or page_number not in expected:
                path.unlink(missing_ok=True)

    def _resize_images(self, image_paths: Sequence[Path]) -> None:
        for image_path in image_paths:
            with Image.open(image_path) as image:
                resized_image = image.convert("RGBA").resize(
                    (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT),
                    Image.Resampling.LANCZOS,
                )
                try:
                    resized_image.save(image_path, format="PNG")
                finally:
                    resized_image.close()

    def _normalize_page_numbers(self, page_numbers: Iterable[int] | None) -> list[int]:
        if not page_numbers:
            return []

        normalized: list[int] = []
        seen: set[int] = set()
        for raw_page_number in page_numbers:
            page_number = int(raw_page_number)
            if page_number < 1 or page_number in seen:
                continue
            normalized.append(page_number)
            seen.add(page_number)
        return normalized

    def _parse_page_number(self, path: Path) -> int | None:
        stem = path.stem
        if not stem.startswith("page-"):
            return None

        raw_page_number = stem.removeprefix("page-").strip()
        return int(raw_page_number) if raw_page_number.isdigit() else None
