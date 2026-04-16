from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import ChatMessage, PageVersion, Project, ProjectPage
from app.models.enums import ChatMessageType, ChatRole, PageStatus
from app.schemas import OutlinePageSchema, OutlineSchema, ProjectCreate
from app.services import PageNotFoundError, PageService, PageVersionNotFoundError, ProjectService

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


@pytest.mark.asyncio
async def test_optimize_existing_page_creates_new_version_and_preserves_title(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await ProjectService(session=session, settings=local_settings).create_project(ProjectCreate(name="Page Service Test"))
        page_service = PageService(session=session, settings=local_settings)
        await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=1,
            title="亮点页",
            page_type="data",
            vue_code=SAMPLE_VUE_CODE,
        )

        optimized_code = SAMPLE_VUE_CODE.replace("hello", "optimized")
        page = await page_service.optimize_existing_page(
            project_id=project.id,
            page_number=1,
            vue_code=optimized_code,
            change_description="标题改为红色",
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

    assert page.version == 2
    assert persisted_page.title == "亮点页"
    assert persisted_page.vue_code == optimized_code
    assert [version.version for version in versions] == [1, 2]
    assert versions[-1].change_description == "标题改为红色"


@pytest.mark.asyncio
async def test_optimize_existing_page_raises_when_page_missing(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await ProjectService(session=session, settings=local_settings).create_project(ProjectCreate(name="Page Service Test"))
        page_service = PageService(session=session, settings=local_settings)

        with pytest.raises(PageNotFoundError):
            await page_service.optimize_existing_page(
                project_id=project.id,
                page_number=9,
                vue_code=SAMPLE_VUE_CODE,
                change_description="missing",
            )


@pytest.mark.asyncio
async def test_confirm_page_marks_existing_page_as_confirmed(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await ProjectService(session=session, settings=local_settings).create_project(ProjectCreate(name="Page Service Test"))
        page_service = PageService(session=session, settings=local_settings)
        await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=1,
            title="封面",
            page_type="cover",
            vue_code=SAMPLE_VUE_CODE,
        )

        page = await page_service.confirm_page(
            project_id=project.id,
            page_number=1,
        )

        persisted_page = (
            await session.execute(
                select(ProjectPage).where(ProjectPage.project_id == project.id, ProjectPage.page_number == 1)
            )
        ).scalar_one()

    assert page.status == PageStatus.CONFIRMED
    assert persisted_page.status == PageStatus.CONFIRMED


@pytest.mark.asyncio
async def test_list_page_versions_returns_descending_versions(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await ProjectService(session=session, settings=local_settings).create_project(ProjectCreate(name="Page Service Test"))
        page_service = PageService(session=session, settings=local_settings)
        await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=1,
            title="封面",
            page_type="cover",
            vue_code=SAMPLE_VUE_CODE,
        )
        await page_service.optimize_existing_page(
            project_id=project.id,
            page_number=1,
            vue_code=SAMPLE_VUE_CODE.replace("hello", "optimized"),
            change_description="标题改为红色",
        )

        versions = await page_service.list_page_versions(
            project_id=project.id,
            page_number=1,
        )

    assert [version.version for version in versions] == [2, 1]
    assert versions[0].change_description == "标题改为红色"


@pytest.mark.asyncio
async def test_rollback_page_to_version_restores_target_code_and_creates_new_version(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await ProjectService(session=session, settings=local_settings).create_project(ProjectCreate(name="Page Service Test"))
        page_service = PageService(session=session, settings=local_settings)
        await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=1,
            title="封面",
            page_type="cover",
            vue_code=SAMPLE_VUE_CODE,
        )
        optimized_code = SAMPLE_VUE_CODE.replace("hello", "optimized")
        latest_page = await page_service.optimize_existing_page(
            project_id=project.id,
            page_number=1,
            vue_code=optimized_code,
            change_description="标题改为红色",
        )
        latest_version_before_rollback = latest_page.version

        rolled_back_page = await page_service.rollback_page_to_version(
            project_id=project.id,
            page_number=1,
            target_version=1,
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

    assert latest_version_before_rollback == 2
    assert rolled_back_page.version == 3
    assert persisted_page.vue_code == SAMPLE_VUE_CODE
    assert [version.version for version in versions] == [1, 2, 3]
    assert versions[1].vue_code == optimized_code
    assert versions[2].vue_code == SAMPLE_VUE_CODE
    assert versions[2].change_description == "回滚到 v1"


@pytest.mark.asyncio
async def test_rollback_page_to_version_raises_when_version_missing(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await ProjectService(session=session, settings=local_settings).create_project(ProjectCreate(name="Page Service Test"))
        page_service = PageService(session=session, settings=local_settings)
        await page_service.upsert_generated_page(
            project_id=project.id,
            page_number=1,
            title="封面",
            page_type="cover",
            vue_code=SAMPLE_VUE_CODE,
        )

        with pytest.raises(PageVersionNotFoundError):
            await page_service.rollback_page_to_version(
                project_id=project.id,
                page_number=1,
                target_version=9,
            )


@pytest.mark.asyncio
async def test_insert_generated_page_after_shifts_pages_outline_messages_and_preview_files(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await seed_crud_project(session=session, settings=local_settings)
        page_service = PageService(session=session, settings=local_settings)
        page_service.write_preview_slide(page_number=1, vue_code=SAMPLE_VUE_CODE.replace("hello", "page-1"))
        page_service.write_preview_slide(page_number=2, vue_code=SAMPLE_VUE_CODE.replace("hello", "page-2"))
        page_service.write_preview_slide(page_number=3, vue_code=SAMPLE_VUE_CODE.replace("hello", "page-3"))

        inserted_page = await page_service.insert_generated_page_after(
            project_id=project.id,
            after_page_number=1,
            outline_page=OutlinePageSchema(
                page_number=2,
                title="新增机会页",
                type="content",
                content_brief="新增机会页",
                layout="title-body",
                data_refs=[],
            ),
            vue_code=SAMPLE_VUE_CODE.replace("hello", "inserted"),
        )

        pages = await load_project_pages(session=session, project_id=project.id)
        messages = await load_page_messages(session=session, project_id=project.id)
        refreshed_project = await session.get(Project, project.id)

    assert inserted_page.page_number == 2
    assert [page.page_number for page in pages] == [1, 2, 3, 4]
    assert [page.title for page in pages] == ["封面", "新增机会页", "经营亮点", "下一步计划"]
    assert refreshed_project is not None
    assert refreshed_project.total_pages == 4
    assert [page["page_number"] for page in refreshed_project.outline["pages"]] == [1, 2, 3, 4]
    assert [page["title"] for page in refreshed_project.outline["pages"]] == ["封面", "新增机会页", "经营亮点", "下一步计划"]
    assert [(message.content, message.page_number) for message in messages] == [
        ("page-1-message", 1),
        ("page-2-message", 3),
        ("page-3-message", 4),
    ]
    assert (local_settings.preview_slides_dir_path / "page-2.vue").read_text(encoding="utf-8") == SAMPLE_VUE_CODE.replace("hello", "inserted")
    assert (local_settings.preview_slides_dir_path / "page-3.vue").read_text(encoding="utf-8") == SAMPLE_VUE_CODE.replace("hello", "page-2-v2")
    assert (local_settings.preview_slides_dir_path / "page-4.vue").read_text(encoding="utf-8") == SAMPLE_VUE_CODE.replace("hello", "page-3")


@pytest.mark.asyncio
async def test_duplicate_page_copies_versions_messages_and_shifts_following_pages(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await seed_crud_project(session=session, settings=local_settings)
        page_service = PageService(session=session, settings=local_settings)

        duplicated_page = await page_service.duplicate_page(project_id=project.id, page_number=2)

        pages = await load_project_pages(session=session, project_id=project.id)
        messages = await load_page_messages(session=session, project_id=project.id)
        duplicated_versions = await load_page_versions_by_number(session=session, project_id=project.id, page_number=3)
        refreshed_project = await session.get(Project, project.id)

    assert duplicated_page.page_number == 3
    assert [page.page_number for page in pages] == [1, 2, 3, 4]
    assert [page.title for page in pages] == ["封面", "经营亮点", "经营亮点", "下一步计划"]
    assert [version.version for version in duplicated_versions] == [1, 2]
    assert [(message.content, message.page_number) for message in messages] == [
        ("page-1-message", 1),
        ("page-2-message", 2),
        ("page-2-message", 3),
        ("page-3-message", 4),
    ]
    assert refreshed_project is not None
    assert [page["page_number"] for page in refreshed_project.outline["pages"]] == [1, 2, 3, 4]
    assert [page["title"] for page in refreshed_project.outline["pages"]] == ["封面", "经营亮点", "经营亮点", "下一步计划"]
    assert (local_settings.preview_slides_dir_path / "page-3.vue").read_text(encoding="utf-8") == SAMPLE_VUE_CODE.replace("hello", "page-2-v2")
    assert (local_settings.preview_slides_dir_path / "page-4.vue").exists()


@pytest.mark.asyncio
async def test_delete_page_removes_target_and_reindexes_pages_outline_messages_and_files(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await seed_crud_project(session=session, settings=local_settings)
        page_service = PageService(session=session, settings=local_settings)
        page_service.write_preview_slide(page_number=1, vue_code=SAMPLE_VUE_CODE.replace("hello", "page-1"))
        page_service.write_preview_slide(page_number=2, vue_code=SAMPLE_VUE_CODE.replace("hello", "page-2-v2"))
        page_service.write_preview_slide(page_number=3, vue_code=SAMPLE_VUE_CODE.replace("hello", "page-3"))

        await page_service.delete_page(project_id=project.id, page_number=2)

        pages = await load_project_pages(session=session, project_id=project.id)
        messages = await load_page_messages(session=session, project_id=project.id)
        refreshed_project = await session.get(Project, project.id)

    assert [page.page_number for page in pages] == [1, 2]
    assert [page.title for page in pages] == ["封面", "下一步计划"]
    assert refreshed_project is not None
    assert refreshed_project.total_pages == 2
    assert [page["page_number"] for page in refreshed_project.outline["pages"]] == [1, 2]
    assert [page["title"] for page in refreshed_project.outline["pages"]] == ["封面", "下一步计划"]
    assert [(message.content, message.page_number) for message in messages] == [
        ("page-1-message", 1),
        ("page-3-message", 2),
    ]
    assert (local_settings.preview_slides_dir_path / "page-2.vue").read_text(encoding="utf-8") == SAMPLE_VUE_CODE.replace("hello", "page-3")
    assert not (local_settings.preview_slides_dir_path / "page-3.vue").exists()


@pytest.mark.asyncio
async def test_reorder_pages_moves_pages_outline_messages_and_preview_files(settings, session_factory) -> None:
    local_settings = settings.model_copy(update={"preview_slides_dir": settings.backend_dir / "preview" / "src" / "slides"})

    async with session_factory() as session:
        project = await seed_crud_project(session=session, settings=local_settings)
        page_service = PageService(session=session, settings=local_settings)

        await page_service.reorder_pages(project_id=project.id, ordered_page_numbers=[3, 1, 2])

        pages = await load_project_pages(session=session, project_id=project.id)
        messages = await load_page_messages(session=session, project_id=project.id)
        refreshed_project = await session.get(Project, project.id)

    assert [page.page_number for page in pages] == [1, 2, 3]
    assert [page.title for page in pages] == ["下一步计划", "封面", "经营亮点"]
    assert refreshed_project is not None
    assert [page["page_number"] for page in refreshed_project.outline["pages"]] == [1, 2, 3]
    assert [page["title"] for page in refreshed_project.outline["pages"]] == ["下一步计划", "封面", "经营亮点"]
    assert [(message.content, message.page_number) for message in messages] == [
        ("page-3-message", 1),
        ("page-1-message", 2),
        ("page-2-message", 3),
    ]
    assert (local_settings.preview_slides_dir_path / "page-1.vue").read_text(encoding="utf-8") == SAMPLE_VUE_CODE.replace("hello", "page-3")
    assert (local_settings.preview_slides_dir_path / "page-2.vue").read_text(encoding="utf-8") == SAMPLE_VUE_CODE.replace("hello", "page-1")
    assert (local_settings.preview_slides_dir_path / "page-3.vue").read_text(encoding="utf-8") == SAMPLE_VUE_CODE.replace("hello", "page-2-v2")


def test_write_preview_slide_uses_redirectable_preview_path(settings) -> None:
    preview_slides_dir = settings.backend_dir / "preview-server" / "src" / "slides"
    local_settings = settings.model_copy(update={"preview_slides_dir": preview_slides_dir})
    page_service = PageService(session=None, settings=local_settings)  # type: ignore[arg-type]

    target_path = page_service.write_preview_slide(page_number=4, vue_code=SAMPLE_VUE_CODE)

    assert target_path == Path(preview_slides_dir / "page-4.vue").resolve()
    assert target_path.read_text(encoding="utf-8") == SAMPLE_VUE_CODE


def test_write_version_preview_slide_uses_redirectable_preview_path(settings) -> None:
    preview_slides_dir = settings.backend_dir / "preview-server" / "src" / "slides"
    local_settings = settings.model_copy(update={"preview_slides_dir": preview_slides_dir})
    page_service = PageService(session=None, settings=local_settings)  # type: ignore[arg-type]

    target_path = page_service.write_version_preview_slide(page_number=4, vue_code=SAMPLE_VUE_CODE)

    assert target_path == Path(preview_slides_dir / "version-preview.vue").resolve()
    assert target_path.read_text(encoding="utf-8") == SAMPLE_VUE_CODE


async def seed_crud_project(*, session, settings) -> Project:
    project_service = ProjectService(session=session, settings=settings)
    project = await project_service.create_project(ProjectCreate(name="Page CRUD Test"))
    await project_service.save_outline(
        project.id,
        OutlineSchema(
            title="Page CRUD Test",
            total_pages=3,
            theme_suggestion="warm-paper",
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
                    title="经营亮点",
                    type="data",
                    content_brief="经营亮点",
                    layout="bullet-grid",
                    data_refs=["metrics.csv"],
                ),
                OutlinePageSchema(
                    page_number=3,
                    title="下一步计划",
                    type="content",
                    content_brief="下一步计划",
                    layout="title-body",
                    data_refs=[],
                ),
            ],
        ),
    )
    page_service = PageService(session=session, settings=settings)
    await page_service.upsert_generated_page(
        project_id=project.id,
        page_number=1,
        title="封面",
        page_type="cover",
        vue_code=SAMPLE_VUE_CODE.replace("hello", "page-1"),
    )
    await page_service.upsert_generated_page(
        project_id=project.id,
        page_number=2,
        title="经营亮点",
        page_type="data",
        vue_code=SAMPLE_VUE_CODE.replace("hello", "page-2"),
    )
    await page_service.optimize_existing_page(
        project_id=project.id,
        page_number=2,
        vue_code=SAMPLE_VUE_CODE.replace("hello", "page-2-v2"),
        change_description="更新经营亮点",
    )
    await page_service.upsert_generated_page(
        project_id=project.id,
        page_number=3,
        title="下一步计划",
        page_type="content",
        vue_code=SAMPLE_VUE_CODE.replace("hello", "page-3"),
    )
    for page_number in (1, 2, 3):
        session.add(
            ChatMessage(
                project_id=project.id,
                page_number=page_number,
                role=ChatRole.USER,
                content=f"page-{page_number}-message",
                message_type=ChatMessageType.TEXT,
            )
        )
    await session.commit()
    return project


async def load_project_pages(*, session, project_id: str) -> list[ProjectPage]:
    stmt = (
        select(ProjectPage)
        .where(ProjectPage.project_id == project_id)
        .options(selectinload(ProjectPage.versions))
        .order_by(ProjectPage.page_number.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def load_page_messages(*, session, project_id: str) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id, ChatMessage.page_number.is_not(None))
        .order_by(ChatMessage.page_number.asc(), ChatMessage.created_at.asc(), ChatMessage.id.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def load_page_versions_by_number(*, session, project_id: str, page_number: int) -> list[PageVersion]:
    page = (
        await session.execute(
            select(ProjectPage).where(ProjectPage.project_id == project_id, ProjectPage.page_number == page_number)
        )
    ).scalar_one()
    stmt = select(PageVersion).where(PageVersion.page_id == page.id).order_by(PageVersion.version.asc())
    return list((await session.execute(stmt)).scalars().all())
