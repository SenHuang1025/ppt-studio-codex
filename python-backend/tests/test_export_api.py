from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.export import router as export_router
from app.api.projects import router as projects_router
from app.config import Settings, get_settings
from app.db import get_db_session
from app.schemas import OutlinePageSchema, OutlineSchema, ProjectCreate
from app.services import ExportProjectSnapshot, ExportTaskManager, PageService, ProjectService, ThemeService

VALID_SFC = """
<template>
  <main style="width: 1920px; height: 1080px; background: var(--slide-bg); color: var(--slide-text);">
    导出测试页
  </main>
</template>
""".strip()


def test_start_pdf_export_task_and_download_artifact(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch,
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(seed_exportable_project(settings=local_settings, session_factory=session_factory))
    manager = ExportTaskManager(settings=local_settings)
    app = build_test_app(settings=local_settings, session_factory=session_factory, export_task_manager=manager)

    async def fake_capture_page_images(
        self: ExportTaskManager,
        *,
        snapshot: ExportProjectSnapshot,
        capture_dir: Path,
        task_id: str,
    ) -> list[Path]:
        capture_dir.mkdir(parents=True, exist_ok=True)
        image_paths: list[Path] = []
        for index, page in enumerate(snapshot.pages, start=1):
            image_path = capture_dir / f"page-{page.page_number:03d}.png"
            image_path.write_bytes(f"page-{page.page_number}".encode("utf-8"))
            image_paths.append(image_path)
            self._update_task(
                task_id,
                stage=f"截图第 {index}/{len(snapshot.pages)} 页",
                completed_pages=index,
                current_page_number=page.page_number,
                current_page_title=page.title,
                progress=min(0.9, 0.1 + index / len(snapshot.pages) * 0.8),
            )
        return image_paths

    def fake_build_pdf_from_images(self: ExportTaskManager, image_paths: list[Path], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-FAKE%")

    monkeypatch.setattr(ExportTaskManager, "_capture_page_images", fake_capture_page_images)
    monkeypatch.setattr(ExportTaskManager, "_build_pdf_from_images", fake_build_pdf_from_images)

    with TestClient(app) as client:
        response = client.post(f"/api/projects/{project_id}/export/pdf")

        assert response.status_code == 202
        task = response.json()
        task_id = task["id"]

        latest_task = task
        for _ in range(20):
            latest_response = client.get(f"/api/projects/{project_id}/export/tasks/{task_id}")
            assert latest_response.status_code == 200
            latest_task = latest_response.json()
            if latest_task["status"] == "completed":
                break
            time.sleep(0.05)

        assert latest_task["status"] == "completed"
        assert latest_task["completed_pages"] == 2
        assert latest_task["artifact_name"].endswith(".pdf")

        download_response = client.get(f"/api/projects/{project_id}/export/tasks/{task_id}/download")

    assert download_response.status_code == 200
    assert download_response.content == b"%PDF-FAKE%"
    assert download_response.headers["content-type"] == "application/pdf"


def test_start_pdf_export_rejects_incomplete_project(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    local_settings = build_local_settings(settings)
    project_id = asyncio.run(seed_incomplete_project(settings=local_settings, session_factory=session_factory))
    manager = ExportTaskManager(settings=local_settings)
    app = build_test_app(settings=local_settings, session_factory=session_factory, export_task_manager=manager)

    with TestClient(app) as client:
        response = client.post(f"/api/projects/{project_id}/export/pdf")

    assert response.status_code == 400
    assert response.json()["detail"] == "当前还有页面未生成完成，请等待全部页面可预览后再导出 PDF。"


def build_test_app(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    export_task_manager: ExportTaskManager,
) -> FastAPI:
    app = FastAPI()
    app.state.export_task_manager = export_task_manager
    app.include_router(projects_router)
    app.include_router(export_router)

    async def override_db_session() -> Any:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings
    return app


def build_local_settings(settings: Settings) -> Settings:
    preview_root = settings.backend_dir / "preview-server"
    return settings.model_copy(
        update={
            "preview_base_url": "http://127.0.0.1:18921",
            "preview_server_dir": preview_root,
            "preview_slides_dir": preview_root / "src" / "slides",
            "preview_theme_file_override": preview_root / "src" / "theme" / "variables.css",
        }
    )


async def seed_exportable_project(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> str:
    async with session_factory() as session:
        project_service = ProjectService(session=session, settings=settings)
        theme_service = ThemeService(settings=settings)
        page_service = PageService(session=session, settings=settings)
        project = await project_service.create_project(ProjectCreate(name="Export Ready Project"))
        await project_service.save_theme_config(project.id, theme_service.resolve_theme(None))
        await project_service.save_outline(
            project.id,
            OutlineSchema(
                title="Export Deck",
                total_pages=2,
                theme_suggestion="warm-orange",
                pages=[
                    OutlinePageSchema(
                        page_number=1,
                        title="封面",
                        type="cover",
                        content_brief="封面",
                        layout="center-hero",
                        data_refs=[],
                    ),
                    OutlinePageSchema(
                        page_number=2,
                        title="目录",
                        type="content",
                        content_brief="目录",
                        layout="title-body",
                        data_refs=[],
                    ),
                ],
            ),
        )
        await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=1,
            title="封面",
            page_type="cover",
            vue_code=VALID_SFC.replace("导出测试页", "封面"),
        )
        await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=2,
            title="目录",
            page_type="content",
            vue_code=VALID_SFC.replace("导出测试页", "目录"),
        )
        return project.id


async def seed_incomplete_project(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> str:
    async with session_factory() as session:
        project_service = ProjectService(session=session, settings=settings)
        theme_service = ThemeService(settings=settings)
        page_service = PageService(session=session, settings=settings)
        project = await project_service.create_project(ProjectCreate(name="Export Partial Project"))
        await project_service.save_theme_config(project.id, theme_service.resolve_theme(None))
        await project_service.save_outline(
            project.id,
            OutlineSchema(
                title="Partial Deck",
                total_pages=2,
                theme_suggestion="warm-orange",
                pages=[
                    OutlinePageSchema(
                        page_number=1,
                        title="封面",
                        type="cover",
                        content_brief="封面",
                        layout="center-hero",
                        data_refs=[],
                    ),
                    OutlinePageSchema(
                        page_number=2,
                        title="总结",
                        type="content",
                        content_brief="总结",
                        layout="title-body",
                        data_refs=[],
                    ),
                ],
            ),
        )
        await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=1,
            title="封面",
            page_type="cover",
            vue_code=VALID_SFC.replace("导出测试页", "封面"),
        )
        return project.id
