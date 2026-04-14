from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services import ChatService


def test_chat_service_lists_project_and_page_history(
    project_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    result = asyncio.run(
        build_chat_history_snapshot(
            project_id=project_id,
            session_factory=session_factory,
        )
    )

    assert [message.content for message in result["global_messages"]] == [
        "请先帮我整理这份季度汇报的结构",
        "已生成《Q1 经营汇报》共 4 页大纲。",
    ]
    assert [message.content for message in result["page_messages"]] == [
        "第 3 页增加一组风险提示",
        "第 3 页建议拆成“风险”与“应对”两栏",
    ]
    assert result["global_total"] == 2
    assert result["page_total"] == 2


def test_chat_service_can_merge_global_and_page_history_for_page_context(
    project_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    result = asyncio.run(
        build_chat_history_snapshot(
            project_id=project_id,
            session_factory=session_factory,
        )
    )

    assert [message.content for message in result["merged_messages"]] == [
        "请先帮我整理这份季度汇报的结构",
        "已生成《Q1 经营汇报》共 4 页大纲。",
        "第 3 页增加一组风险提示",
        "第 3 页建议拆成“风险”与“应对”两栏",
    ]
    assert result["merged_total"] == 4


def test_chat_service_build_agent_history_returns_stable_summarized_context(
    project_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    history = asyncio.run(
        build_agent_history(
            project_id=project_id,
            session_factory=session_factory,
        )
    )

    assert [message["content"] for message in history] == [
        "请先帮我整理这份季度汇报的结构",
        "已生成《Q1 经营汇报》共 4 页大纲。",
        "第 3 页增加一组风险提示",
        "第 3 页建议拆成“风险”与“应对”两栏",
    ]
    assert history[1]["message_type"] == "outline"
    assert history[1]["metadata"] == {
        "outline_title": "Q1 经营汇报",
        "page_titles": ["封面", "目录", "经营亮点", "风险提示"],
        "theme_suggestion": "warm-paper",
        "total_pages": 4,
    }


async def build_chat_history_snapshot(
    *,
    project_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, object]:
    async with session_factory() as session:
        service = ChatService(session=session)
        await seed_messages(service, project_id=project_id)

        global_messages, global_total = await service.list_messages(project_id)
        page_messages, page_total = await service.list_messages(project_id, page_number=3)
        merged_messages, merged_total = await service.list_messages(
            project_id,
            page_number=3,
            include_global_for_page=True,
        )

        return {
            "global_messages": global_messages,
            "global_total": global_total,
            "merged_messages": merged_messages,
            "merged_total": merged_total,
            "page_messages": page_messages,
            "page_total": page_total,
        }


async def build_agent_history(
    *,
    project_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> list[dict[str, object]]:
    async with session_factory() as session:
        service = ChatService(session=session)
        await seed_messages(service, project_id=project_id)
        return await service.build_agent_history(project_id, page_number=3, limit=10)


async def seed_messages(service: ChatService, *, project_id: str) -> None:
    existing_messages, _ = await service.list_messages(project_id, include_global_for_page=True, page_number=3)
    if existing_messages:
        return

    base_time = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    messages = [
        await service.create_message(
            project_id=project_id,
            role="user",
            content="请先帮我整理这份季度汇报的结构",
            message_type="text",
        ),
        await service.create_message(
            project_id=project_id,
            role="assistant",
            content="已生成《Q1 经营汇报》共 4 页大纲。",
            message_type="outline",
            metadata={
                "outline": {
                    "title": "Q1 经营汇报",
                    "total_pages": 4,
                    "theme_suggestion": "warm-paper",
                    "pages": [
                        {"title": "封面"},
                        {"title": "目录"},
                        {"title": "经营亮点"},
                        {"title": "风险提示"},
                    ],
                }
            },
        ),
        await service.create_message(
            project_id=project_id,
            role="user",
            content="第 3 页增加一组风险提示",
            message_type="text",
            page_number=3,
        ),
        await service.create_message(
            project_id=project_id,
            role="assistant",
            content="第 3 页建议拆成“风险”与“应对”两栏",
            message_type="text",
            page_number=3,
        ),
        await service.create_message(
            project_id=project_id,
            role="user",
            content="第 5 页改成客户案例页",
            message_type="text",
            page_number=5,
        ),
    ]

    for index, message in enumerate(messages):
        message.created_at = base_time + timedelta(minutes=index)

    await service.session.commit()
    for message in messages:
        await service.session.refresh(message)
