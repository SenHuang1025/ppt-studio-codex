from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from loguru import logger
from PIL import Image

from app.config import Settings
from app.schemas import ProjectExportFormat, ProjectExportStatus, ThemeConfig
from app.services.preview_capture_service import (
    PreviewCaptureDependencyError,
    PreviewCaptureRenderError,
    PreviewCaptureService,
)
from app.services.theme_service import ThemeService

SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080


class ExportServiceError(Exception):
    """Base exception for export service failures."""


class ExportTaskNotFoundError(ExportServiceError):
    def __init__(self, project_id: str, task_id: str):
        super().__init__(f"Export task '{task_id}' was not found for project '{project_id}'.")
        self.project_id = project_id
        self.task_id = task_id


class ExportValidationError(ExportServiceError):
    """Raised when the export request cannot be executed on the current project state."""


class ExportConflictError(ExportServiceError):
    """Raised when another export task is already running."""


class ExportDependencyError(ExportServiceError):
    """Raised when export runtime dependencies are unavailable."""


class ExportRenderError(ExportServiceError):
    """Raised when preview capture or PDF generation fails."""


class ExportArtifactNotReadyError(ExportServiceError):
    """Raised when the requested export artifact is not ready for download."""


@dataclass(frozen=True, slots=True)
class ExportPageSnapshot:
    page_number: int
    title: str
    vue_code: str


@dataclass(frozen=True, slots=True)
class ExportProjectSnapshot:
    project_id: str
    project_name: str
    total_pages: int
    theme: ThemeConfig
    pages: tuple[ExportPageSnapshot, ...]


@dataclass(slots=True)
class ExportTaskRecord:
    id: str
    project_id: str
    export_format: ProjectExportFormat
    total_pages: int
    status: ProjectExportStatus = ProjectExportStatus.PENDING
    stage: str = "等待开始"
    completed_pages: int = 0
    current_page_number: int | None = None
    current_page_title: str | None = None
    progress: float = 0.0
    error: str | None = None
    artifact_name: str | None = None
    artifact_path: Path | None = None
    artifact_size_bytes: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExportTaskManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.theme_service = ThemeService(settings=settings)
        self.capture_service = PreviewCaptureService(preview_base_url=settings.preview_base_url)
        self._tasks: dict[str, ExportTaskRecord] = {}
        self._active_task_id: str | None = None

    async def start_pdf_export(self, snapshot: ExportProjectSnapshot) -> ExportTaskRecord:
        if not snapshot.pages:
            raise ExportValidationError("当前项目还没有可导出的页面。")

        active_task = self._resolve_active_task()
        if active_task is not None:
            raise ExportConflictError(
                f"导出任务 {active_task.id} 正在执行，请等待当前导出完成后再试。"
            )

        task_id = uuid.uuid4().hex
        task = ExportTaskRecord(
            id=task_id,
            project_id=snapshot.project_id,
            export_format=ProjectExportFormat.PDF,
            total_pages=len(snapshot.pages),
        )
        self._tasks[task_id] = task
        self._active_task_id = task_id
        asyncio.create_task(self._run_pdf_export(task_id=task_id, snapshot=snapshot))
        return task

    def get_task(self, *, project_id: str, task_id: str) -> ExportTaskRecord:
        task = self._tasks.get(task_id)
        if task is None or task.project_id != project_id:
            raise ExportTaskNotFoundError(project_id, task_id)
        return task

    def require_artifact(self, *, project_id: str, task_id: str) -> tuple[ExportTaskRecord, Path]:
        task = self.get_task(project_id=project_id, task_id=task_id)
        artifact_path = task.artifact_path

        if task.status != ProjectExportStatus.COMPLETED or artifact_path is None or not artifact_path.exists():
            raise ExportArtifactNotReadyError("导出文件尚未生成完成。")

        return task, artifact_path

    async def _run_pdf_export(self, *, task_id: str, snapshot: ExportProjectSnapshot) -> None:
        task_dir = self._task_dir(project_id=snapshot.project_id, task_id=task_id)
        capture_dir = task_dir / "captures"
        capture_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._update_task(
                task_id,
                status=ProjectExportStatus.RUNNING,
                stage="准备导出预览资源",
                progress=0.05,
            )

            image_paths = await self._capture_page_images(
                snapshot=snapshot,
                capture_dir=capture_dir,
                task_id=task_id,
            )
            self._update_task(
                task_id,
                stage="合并 PDF",
                progress=0.95,
                completed_pages=len(image_paths),
            )

            output_path = task_dir / self._build_pdf_filename(snapshot.project_name)
            await asyncio.to_thread(self._build_pdf_from_images, image_paths, output_path)

            self._update_task(
                task_id,
                status=ProjectExportStatus.COMPLETED,
                stage="导出完成",
                progress=1.0,
                completed_pages=len(snapshot.pages),
                current_page_number=None,
                current_page_title=None,
                artifact_name=output_path.name,
                artifact_path=output_path,
                artifact_size_bytes=output_path.stat().st_size,
                error=None,
            )
        except Exception as exc:
            logger.exception("PDF export task {} failed for project {}", task_id, snapshot.project_id)
            self._update_task(
                task_id,
                status=ProjectExportStatus.FAILED,
                stage="导出失败",
                error=str(exc) or exc.__class__.__name__,
            )
        finally:
            if self._active_task_id == task_id:
                self._active_task_id = None

    async def _capture_page_images(
        self,
        *,
        snapshot: ExportProjectSnapshot,
        capture_dir: Path,
        task_id: str,
    ) -> list[Path]:
        try:
            return await self.capture_service.capture_slide_images(
                page_numbers=[snapshot_page.page_number for snapshot_page in snapshot.pages],
                capture_dir=capture_dir,
                before_capture=lambda: asyncio.to_thread(self._sync_preview_snapshot, snapshot),
                file_name_resolver=lambda page_number: f"page-{page_number:03d}.png",
                on_page_start=lambda index, total, page_number: self._update_export_capture_progress(
                    task_id=task_id,
                    index=index,
                    total=total,
                    page_number=page_number,
                    snapshot=snapshot,
                ),
            )
        except PreviewCaptureDependencyError as exc:
            raise ExportDependencyError(
                str(exc),
            ) from exc
        except PreviewCaptureRenderError as exc:
            raise ExportRenderError(str(exc)) from exc

    def _update_export_capture_progress(
        self,
        *,
        task_id: str,
        index: int,
        total: int,
        page_number: int,
        snapshot: ExportProjectSnapshot,
    ) -> None:
        snapshot_page = next((page for page in snapshot.pages if page.page_number == page_number), None)
        self._update_task(
            task_id,
            stage=f"截图第 {index}/{total} 页",
            progress=self._capture_progress(index=index, total=total),
            completed_pages=index - 1,
            current_page_number=page_number,
            current_page_title=snapshot_page.title if snapshot_page is not None else None,
        )

    def _sync_preview_snapshot(self, snapshot: ExportProjectSnapshot) -> None:
        self.theme_service.write_preview_theme(snapshot.theme)
        self._sync_preview_slides(snapshot.pages)

    def _sync_preview_slides(self, pages: Sequence[ExportPageSnapshot]) -> None:
        slides_dir = self.settings.preview_slides_dir_path.resolve()
        slides_dir.mkdir(parents=True, exist_ok=True)
        expected_page_numbers = {page.page_number for page in pages}

        for page in pages:
            target_path = (slides_dir / f"page-{page.page_number}.vue").resolve()
            if not target_path.is_relative_to(slides_dir):
                raise ExportRenderError(f"Unsafe preview slide path resolved: {target_path}")
            target_path.write_text(page.vue_code, encoding="utf-8")

        for path in slides_dir.glob("page-*.vue"):
            page_number = self._parse_page_number(path)
            if page_number is None or page_number not in expected_page_numbers:
                path.unlink(missing_ok=True)

    def _build_pdf_from_images(self, image_paths: Sequence[Path], output_path: Path) -> None:
        if not image_paths:
            raise ExportValidationError("没有可用于生成 PDF 的页面截图。")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas
        except ModuleNotFoundError:
            self._build_pdf_with_pillow(image_paths, output_path)
            return

        pdf_canvas = canvas.Canvas(str(output_path), pagesize=(SLIDE_WIDTH, SLIDE_HEIGHT))
        for image_path in image_paths:
            pdf_canvas.drawImage(
                ImageReader(str(image_path)),
                0,
                0,
                width=SLIDE_WIDTH,
                height=SLIDE_HEIGHT,
                preserveAspectRatio=True,
                mask="auto",
            )
            pdf_canvas.showPage()
        pdf_canvas.save()

    def _build_pdf_with_pillow(self, image_paths: Sequence[Path], output_path: Path) -> None:
        images = [Image.open(image_path).convert("RGB") for image_path in image_paths]

        try:
            first_image, *other_images = images
            first_image.save(output_path, "PDF", save_all=True, append_images=other_images)
        finally:
            for image in images:
                image.close()

    def _build_pdf_filename(self, project_name: str) -> str:
        slug = self._slugify(project_name) or "ppt-studio-export"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{slug}-{timestamp}.pdf"

    def _slugify(self, value: str) -> str:
        normalized = re.sub(r"\s+", "-", value.strip().lower())
        normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff_-]+", "-", normalized)
        normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
        return normalized[:80]

    def _task_dir(self, *, project_id: str, task_id: str) -> Path:
        project_dir = self.settings.project_dir(project_id).resolve()
        export_root = (project_dir / "exports").resolve()

        if not export_root.is_relative_to(project_dir):
            raise ExportRenderError(f"Unsafe export directory resolved for project '{project_id}'.")

        task_dir = (export_root / task_id).resolve()
        if not task_dir.is_relative_to(export_root):
            raise ExportRenderError(f"Unsafe export task directory resolved for task '{task_id}'.")

        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir

    def _resolve_active_task(self) -> ExportTaskRecord | None:
        if self._active_task_id is None:
            return None

        task = self._tasks.get(self._active_task_id)
        if task is None:
            self._active_task_id = None
            return None

        if task.status not in {ProjectExportStatus.PENDING, ProjectExportStatus.RUNNING}:
            self._active_task_id = None
            return None

        return task

    def _update_task(self, task_id: str, **changes: object) -> None:
        task = self._tasks.get(task_id)
        if task is None:
            return

        for field_name, value in changes.items():
            setattr(task, field_name, value)
        task.updated_at = datetime.now(timezone.utc)

    def _capture_progress(self, *, index: int, total: int) -> float:
        if total <= 0:
            return 0.1
        return min(0.9, 0.1 + (index / total) * 0.8)

    def _parse_page_number(self, path: Path) -> int | None:
        stem = path.stem
        if not stem.startswith("page-"):
            return None

        raw_page_number = stem.removeprefix("page-").strip()
        return int(raw_page_number) if raw_page_number.isdigit() else None
