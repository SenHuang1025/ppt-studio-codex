from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import PageVersion, ProjectPage
from app.schemas import ProjectCreate
from app.services import PageService, ProjectService

SAMPLE_VUE_CODE = """
<script setup lang="ts">
const message = 'hello'
</script>

<template>
  <main class="slide-page">{{ message }}</main>
</template>

<style scoped>
.slide-page {
  width: 1920px;
  height: 1080px;
}
</style>
""".strip()


@pytest.mark.asyncio
async def test_upsert_generated_page_creates_page_and_initial_version(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await ProjectService(session=session, settings=local_settings).create_project(ProjectCreate(name="Page Service Test"))
        page_service = PageService(session=session, settings=local_settings)

        page = await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=1,
            title="封面",
            page_type="cover",
            vue_code=SAMPLE_VUE_CODE,
        )

        persisted_page = (
            await session.execute(
                select(ProjectPage).where(ProjectPage.project_id == project.id, ProjectPage.page_number == 1)
            )
        ).scalar_one()
        versions = list(
            (
                await session.execute(select(PageVersion).where(PageVersion.page_id == persisted_page.id).order_by(PageVersion.version))
            ).scalars()
        )

    assert page.version == 1
    assert persisted_page.title == "封面"
    assert persisted_page.page_type == "cover"
    assert persisted_page.vue_code == SAMPLE_VUE_CODE
    assert len(versions) == 1
    assert versions[0].version == 1
    assert versions[0].vue_code == SAMPLE_VUE_CODE


@pytest.mark.asyncio
async def test_upsert_generated_page_increments_version_on_regeneration(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await ProjectService(session=session, settings=local_settings).create_project(ProjectCreate(name="Page Service Test"))
        page_service = PageService(session=session, settings=local_settings)
        await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=2,
            title="数据页",
            page_type="data",
            vue_code=SAMPLE_VUE_CODE,
        )

        regenerated_code = SAMPLE_VUE_CODE.replace("hello", "updated")
        page = await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=2,
            title="数据页优化版",
            page_type="data",
            vue_code=regenerated_code,
        )

        persisted_page = (
            await session.execute(
                select(ProjectPage).where(ProjectPage.project_id == project.id, ProjectPage.page_number == 2)
            )
        ).scalar_one()
        versions = list(
            (
                await session.execute(select(PageVersion).where(PageVersion.page_id == persisted_page.id).order_by(PageVersion.version))
            ).scalars()
        )

    assert page.version == 2
    assert persisted_page.title == "数据页优化版"
    assert persisted_page.vue_code == regenerated_code
    assert [version.version for version in versions] == [1, 2]
    assert versions[-1].vue_code == regenerated_code


def test_write_preview_slide_uses_redirectable_preview_path(settings) -> None:
    preview_slides_dir = settings.backend_dir / "preview-server" / "src" / "slides"
    local_settings = settings.model_copy(update={"preview_slides_dir": preview_slides_dir})
    page_service = PageService(session=None, settings=local_settings)  # type: ignore[arg-type]

    target_path = page_service.write_preview_slide(page_number=4, vue_code=SAMPLE_VUE_CODE)

    assert target_path == Path(preview_slides_dir / "page-4.vue").resolve()
    assert target_path.read_text(encoding="utf-8") == SAMPLE_VUE_CODE
