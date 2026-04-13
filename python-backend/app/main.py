from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import router
from app.config import get_settings
from app.db import close_database, init_database
from app.logging import configure_logging
from app.services import SSEManager


def create_app() -> FastAPI:
    settings = get_settings()
    settings.ensure_directories()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "Starting backend with env={}, host={}, port={}, data_dir={}",
            settings.environment,
            settings.host,
            settings.port,
            settings.data_dir,
        )
        logger.info("Initializing SQLite database at {}", settings.database_path)
        await init_database()
        app.state.database_url = settings.database_url
        app.state.sse_manager = SSEManager()
        yield
        await app.state.sse_manager.shutdown()
        await close_database()
        logger.info("Stopping backend")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_origin_regex=settings.cors_allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    return app


app = create_app()
