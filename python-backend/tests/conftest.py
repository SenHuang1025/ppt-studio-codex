from __future__ import annotations

from pathlib import Path

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.config import Settings
from app.db.base import Base
from app.schemas import ProjectCreate
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    settings = Settings(
        backend_dir=tmp_path,
        data_dir=data_dir,
        log_dir=data_dir / "logs",
    )
    settings.ensure_directories()
    return settings


@pytest_asyncio.fixture
async def session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, future=True)
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def project_id(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> str:
    async with session_factory() as session:
        project_service = ProjectService(session=session, settings=settings)
        project = await project_service.create_project(ProjectCreate(name="Parser Test Project"))
        return project.id
