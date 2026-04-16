from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.chat import router as chat_router
from app.api.projects import router as projects_router
from app.config import Settings, get_settings
from app.db import get_db_session
from app.schemas import ProjectCreate
from app.services import ChatService, ProjectService


def test_chat_api_lists_project_level_messages(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    project_id = asyncio.run(seed_chat_api_project(settings=settings, session_factory=session_factory))
    app = build_test_app(settings=settings, session_factory=session_factory)

    with TestClient(app) as client:
        response = client.get(f"/api/projects/{project_id}/chat/messages")

    payload = response.json()

    assert response.status_code == 200
    assert payload["total"] == 2
    assert [message["content"] for message in payload["messages"]] == [
        "请先规划项目级大纲",
        "已生成《项目总览》共 3 页大纲。",
    ]
    assert payload["messages"][1]["metadata"]["outline"]["title"] == "项目总览"


def test_chat_api_can_include_global_messages_for_page_history(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    project_id = asyncio.run(seed_chat_api_project(settings=settings, session_factory=session_factory))
    app = build_test_app(settings=settings, session_factory=session_factory)

    with TestClient(app) as client:
        page_only_response = client.get(f"/api/projects/{project_id}/chat/messages?page_number=3")
        merged_response = client.get(
            f"/api/projects/{project_id}/chat/messages?page_number=3&include_global=true",
        )

    page_only_payload = page_only_response.json()
    merged_payload = merged_response.json()

    assert page_only_response.status_code == 200
    assert merged_response.status_code == 200
    assert page_only_payload["total"] == 1
    assert [message["content"] for message in page_only_payload["messages"]] == ["第 3 页需要加一组关键风险"]
    assert merged_payload["total"] == 3
    assert [message["content"] for message in merged_payload["messages"]] == [
        "请先规划项目级大纲",
        "已生成《项目总览》共 3 页大纲。",
        "第 3 页需要加一组关键风险",
    ]


def test_chat_api_can_include_page_messages_in_project_history(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    project_id = asyncio.run(seed_chat_api_project(settings=settings, session_factory=session_factory))
    app = build_test_app(settings=settings, session_factory=session_factory)

    with TestClient(app) as client:
      response = client.get(f"/api/projects/{project_id}/chat/messages?include_page_messages=true")

    payload = response.json()

    assert response.status_code == 200
    assert payload["total"] == 3
    assert [message["content"] for message in payload["messages"]] == [
        "请先规划项目级大纲",
        "已生成《项目总览》共 3 页大纲。",
        "第 3 页需要加一组关键风险",
    ]
    assert payload["messages"][2]["page_number"] == 3


def test_project_detail_includes_page_chat_message_counts(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    project_id = asyncio.run(seed_chat_api_project(settings=settings, session_factory=session_factory))
    app = build_test_app(settings=settings, session_factory=session_factory)
    asyncio.run(seed_page_records(settings=settings, session_factory=session_factory, project_id=project_id))

    with TestClient(app) as client:
        response = client.get(f"/api/projects/{project_id}")

    payload = response.json()

    assert response.status_code == 200
    assert [page["page_number"] for page in payload["pages"]] == [1, 3]
    assert payload["pages"][0]["chat_message_count"] == 0
    assert payload["pages"][1]["chat_message_count"] == 1


def build_test_app(*, settings: Settings, session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    app = FastAPI()
    app.include_router(projects_router)
    app.include_router(chat_router)

    async def override_db_session() -> Any:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings
    return app


async def seed_chat_api_project(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> str:
    async with session_factory() as session:
        project_service = ProjectService(session=session, settings=settings)
        project = await project_service.create_project(ProjectCreate(name="Chat API Test Project"))
        chat_service = ChatService(session=session)

        messages = [
            await chat_service.create_message(
                project_id=project.id,
                role="user",
                content="请先规划项目级大纲",
                message_type="text",
            ),
            await chat_service.create_message(
                project_id=project.id,
                role="assistant",
                content="已生成《项目总览》共 3 页大纲。",
                message_type="outline",
                metadata={
                    "outline": {
                        "title": "项目总览",
                        "total_pages": 3,
                        "theme_suggestion": "warm-paper",
                        "pages": [{"title": "封面"}, {"title": "目录"}, {"title": "关键结论"}],
                    }
                },
            ),
            await chat_service.create_message(
                project_id=project.id,
                role="user",
                content="第 3 页需要加一组关键风险",
                message_type="text",
                page_number=3,
            ),
        ]

        base_time = datetime(2026, 4, 13, 9, 0, tzinfo=timezone.utc)
        for index, message in enumerate(messages):
            message.created_at = base_time + timedelta(minutes=index)

        await session.commit()
        return project.id


async def seed_page_records(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    project_id: str,
) -> None:
    from app.services import PageService

    async with session_factory() as session:
        page_service = PageService(session=session, settings=settings)
        await page_service.upsert_generated_page(
            project_id=project_id,
            page_number=1,
            title="封面",
            page_type="cover",
            vue_code="<script setup lang=\"ts\"></script><template><main></main></template>",
        )
        await page_service.upsert_generated_page(
            project_id=project_id,
            page_number=3,
            title="关键结论",
            page_type="content",
            vue_code="<script setup lang=\"ts\"></script><template><main></main></template>",
        )
