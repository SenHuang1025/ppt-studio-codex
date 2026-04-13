from __future__ import annotations

from collections.abc import AsyncIterator
from sqlite3 import Connection as SQLite3Connection

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.base import Base

settings = get_settings()

async_engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,
)

AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    autoflush=False,
)


@event.listens_for(async_engine.sync_engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection: SQLite3Connection, _: object) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session


async def init_database() -> None:
    import app.models  # noqa: F401

    settings.ensure_directories()

    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    await async_engine.dispose()
