from __future__ import annotations

import sys

from loguru import logger

from app.config import Settings


def configure_logging(settings: Settings) -> None:
    logger.remove()

    log_level = "DEBUG" if settings.environment == "development" else "INFO"
    log_file = settings.log_dir / "backend.log"

    logger.add(
        sys.stderr,
        level=log_level,
        backtrace=settings.environment == "development",
        diagnose=settings.environment == "development",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )
    logger.add(
        log_file,
        level=log_level,
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )
