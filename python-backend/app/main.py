from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError

from app.api import router
from app.config import get_settings
from app.db import close_database, init_database
from app.logging import configure_logging
from app.schemas import ErrorResponse
from app.services import ExportTaskManager, SSEManager, ThumbnailService


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
        app.state.export_task_manager = ExportTaskManager(settings=settings)
        app.state.thumbnail_service = ThumbnailService(settings=settings)
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
    register_exception_handlers(app)
    app.include_router(router)

    return app


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
        detail_message = _stringify_http_detail(exc.detail)
        error_message = detail_message or _default_status_error_message(exc.status_code)
        logger.warning("HTTP {}: {}", exc.status_code, error_message)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(error=error_message, detail=detail_message).model_dump(mode="json"),
        )

    @app.exception_handler(ValidationError)
    async def handle_validation_exception(_request: Request, exc: ValidationError) -> JSONResponse:
        detail_message = exc.errors(include_url=False)
        logger.warning("Validation error: {}", detail_message)
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(error="请求参数校验失败。", detail=str(detail_message)).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled backend exception")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="服务器内部发生异常，请稍后重试。",
                detail=str(exc) or exc.__class__.__name__,
            ).model_dump(mode="json"),
        )


def _stringify_http_detail(detail: object) -> str | None:
    if detail is None:
        return None

    if isinstance(detail, str):
        normalized = detail.strip()
        return normalized or None

    if isinstance(detail, list):
        normalized_items = [str(item).strip() for item in detail if str(item).strip()]
        return "; ".join(normalized_items) if normalized_items else None

    normalized = str(detail).strip()
    return normalized or None


def _default_status_error_message(status_code: int) -> str:
    if status_code == 400:
        return "请求失败，请检查输入后重试。"
    if status_code == 401:
        return "认证失败，请重新配置 API Key 后重试。"
    if status_code == 403:
        return "当前请求未被允许执行。"
    if status_code == 404:
        return "请求的资源不存在。"
    if status_code == 409:
        return "当前请求与系统状态冲突，请刷新后重试。"
    if status_code == 422:
        return "请求参数校验失败。"
    if status_code >= 500:
        return "服务器内部发生异常，请稍后重试。"
    return "请求失败，请稍后重试。"


app = create_app()
