from __future__ import annotations

from functools import lru_cache
from os import getenv
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str = "PPT Studio Python Backend"
    app_version: str = "0.1.0"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 18922
    backend_dir: Path
    data_dir: Path
    log_dir: Path
    database_filename: str = "ppt_studio.db"
    sql_echo: bool = False
    preview_base_url: str = "http://127.0.0.1:18921"
    preview_server_dir: Path | None = None
    preview_slides_dir: Path | None = None
    preview_theme_file_override: Path | None = None
    cors_allow_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "null",
    )
    cors_allow_origin_regex: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    @classmethod
    def from_env(cls) -> "Settings":
        backend_dir = Path(__file__).resolve().parents[1]
        data_dir_raw = getenv("PPT_STUDIO_DATA_DIR")
        data_dir = (
            Path(data_dir_raw).expanduser().resolve()
            if data_dir_raw
            else backend_dir / "data"
        )
        preview_slides_dir_raw = getenv("PPT_STUDIO_PREVIEW_SLIDES_DIR")
        preview_server_dir_raw = getenv("PPT_STUDIO_PREVIEW_SERVER_DIR")
        preview_theme_file_raw = getenv("PPT_STUDIO_PREVIEW_THEME_FILE")
        preview_base_url_raw = getenv("PPT_STUDIO_PREVIEW_BASE_URL")
        port_raw = getenv("PPT_STUDIO_PORT")
        sql_echo_raw = getenv("PPT_STUDIO_SQL_ECHO", "0").strip().lower()

        return cls(
            environment=getenv("PPT_STUDIO_ENV", "development"),
            host=getenv("PPT_STUDIO_HOST", "127.0.0.1"),
            port=int(port_raw) if port_raw else 18922,
            backend_dir=backend_dir,
            data_dir=data_dir,
            log_dir=data_dir / "logs",
            preview_base_url=(preview_base_url_raw or "http://127.0.0.1:18921").strip().rstrip("/"),
            preview_server_dir=(
                Path(preview_server_dir_raw).expanduser().resolve()
                if preview_server_dir_raw
                else None
            ),
            preview_slides_dir=(
                Path(preview_slides_dir_raw).expanduser().resolve()
                if preview_slides_dir_raw
                else None
            ),
            preview_theme_file_override=(
                Path(preview_theme_file_raw).expanduser().resolve()
                if preview_theme_file_raw
                else None
            ),
            sql_echo=sql_echo_raw in {"1", "true", "yes", "on"},
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    @property
    def database_path(self) -> Path:
        return self.data_dir / self.database_filename

    @property
    def projects_dir(self) -> Path:
        return self.data_dir / "projects"

    def project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    @property
    def preview_theme_file_path(self) -> Path:
        if self.preview_theme_file_override is not None:
            return self.preview_theme_file_override

        return self.preview_slides_dir_path.parent / "theme" / "variables.css"

    @property
    def preview_server_dir_path(self) -> Path:
        if self.preview_server_dir is not None:
            return self.preview_server_dir

        return self.backend_dir.parent / "ppt-preview-server"

    @property
    def preview_slides_dir_path(self) -> Path:
        if self.preview_slides_dir is not None:
            return self.preview_slides_dir

        return self.preview_server_dir_path / "src" / "slides"

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.database_path.resolve().as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
