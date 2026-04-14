from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.config import Settings
from app.db.base import Base
from app.schemas import ProjectCreate
from app.services.project_service import ProjectService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    settings = Settings(
        backend_dir=tmp_path,
        data_dir=data_dir,
        log_dir=data_dir / "logs",
    )
    settings.ensure_directories()
    return settings


@pytest.fixture
def session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, future=True)
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async def initialize_database() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(initialize_database())

    try:
        yield session_factory
    finally:
        asyncio.run(engine.dispose())


@pytest.fixture
def project_id(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> str:
    async def create_project_id() -> str:
        async with session_factory() as session:
            project_service = ProjectService(session=session, settings=settings)
            project = await project_service.create_project(ProjectCreate(name="Parser Test Project"))
            return project.id

    return asyncio.run(create_project_id())
