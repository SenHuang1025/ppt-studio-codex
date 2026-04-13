from __future__ import annotations

import asyncio
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from loguru import logger
from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.base import generate_uuid
from app.models import Project, UploadedFile
from app.models.enums import FileParseStatus
from app.parsers import parse as parse_uploaded_file
from app.services.project_service import ProjectNotFoundError


class FileServiceError(Exception):
    """Base exception for file service failures."""


class FileValidationError(FileServiceError):
    """Raised when the uploaded file does not satisfy API constraints."""


class UnsupportedFileTypeError(FileValidationError):
    """Raised when the uploaded file extension is not allowed."""


class FileTooLargeError(FileValidationError):
    """Raised when the uploaded file exceeds the maximum allowed size."""


class UploadedFileNotFoundError(FileServiceError):
    def __init__(self, project_id: str, file_id: str):
        super().__init__(f"Uploaded file '{file_id}' was not found in project '{project_id}'.")
        self.project_id = project_id
        self.file_id = file_id


class FileStorageError(FileServiceError):
    """Raised when file persistence or path resolution fails."""


class FileParsingError(FileServiceError):
    def __init__(self, project_id: str, file_id: str):
        super().__init__(f"Failed to parse uploaded file '{file_id}' in project '{project_id}'.")
        self.project_id = project_id
        self.file_id = file_id


class FileService:
    ALLOWED_FILE_TYPES: tuple[str, ...] = (
        "xlsx",
        "csv",
        "docx",
        "pdf",
        "pptx",
        "png",
        "jpg",
        "jpeg",
        "md",
        "json",
        "txt",
    )
    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
    CHUNK_SIZE_BYTES = 1024 * 1024

    def __init__(self, session: AsyncSession, settings: Settings):
        self.session = session
        self.settings = settings

    async def list_files(self, project_id: str) -> list[UploadedFile]:
        await self._ensure_project_exists(project_id)

        stmt: Select[tuple[UploadedFile]] = (
            select(UploadedFile)
            .where(UploadedFile.project_id == project_id)
            .order_by(UploadedFile.created_at.desc(), UploadedFile.id.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def upload_file(self, project_id: str, upload_file: UploadFile) -> UploadedFile:
        await self._ensure_project_exists(project_id)

        original_name = self._normalize_original_name(getattr(upload_file, "filename", None))
        file_type = self._extract_file_type(original_name)
        file_id = generate_uuid()
        relative_file_path = Path("uploads") / f"{file_id}{Path(original_name).suffix.lower()}"
        resolved_file_path = self._resolve_project_file_path(project_id, relative_file_path)
        file_size = 0

        try:
            file_size = await self._write_upload_to_disk(upload_file, resolved_file_path)

            uploaded_file = UploadedFile(
                id=file_id,
                project_id=project_id,
                original_name=original_name,
                file_type=file_type,
                file_path=relative_file_path.as_posix(),
                file_size=file_size,
                parse_status=FileParseStatus.PENDING,
            )
            self.session.add(uploaded_file)
            await self.session.commit()
            await self.session.refresh(uploaded_file)
        except (FileServiceError, OSError, SQLAlchemyError) as exc:
            await self.session.rollback()
            await self._remove_file_if_exists(resolved_file_path)

            if isinstance(exc, FileServiceError):
                raise

            raise FileStorageError(f"Failed to persist uploaded file '{original_name}'.") from exc
        finally:
            await upload_file.close()

        logger.info(
            "Uploaded file {} for project {} to {} ({} bytes)",
            original_name,
            project_id,
            resolved_file_path,
            file_size,
        )
        return uploaded_file

    async def delete_file(self, project_id: str, file_id: str) -> None:
        await self._ensure_project_exists(project_id)
        uploaded_file = await self._get_uploaded_file_or_raise(project_id, file_id)
        resolved_file_path = self._resolve_stored_file_path(project_id, uploaded_file.file_path)

        await self.session.delete(uploaded_file)

        try:
            await self.session.commit()
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise FileStorageError(f"Failed to delete uploaded file '{file_id}'.") from exc

        try:
            await self._remove_file_if_exists(resolved_file_path)
        except OSError as exc:
            logger.warning(
                "Uploaded file record {} was deleted but storage cleanup failed for {}: {}",
                file_id,
                resolved_file_path,
                exc,
            )

        logger.info("Deleted uploaded file {} from project {}", file_id, project_id)

    async def parse_file(self, project_id: str, file_id: str, force: bool = False) -> UploadedFile:
        await self._ensure_project_exists(project_id)
        uploaded_file = await self._get_uploaded_file_or_raise(project_id, file_id)

        if not force:
            if uploaded_file.parse_status == FileParseStatus.PARSED and uploaded_file.parsed_content is not None:
                return uploaded_file
            if uploaded_file.parse_status == FileParseStatus.PARSING:
                return uploaded_file

        resolved_file_path = self._resolve_stored_file_path(project_id, uploaded_file.file_path)
        await self._update_parse_state(
            uploaded_file,
            parse_status=FileParseStatus.PARSING,
            parsed_content=None,
        )

        try:
            if not resolved_file_path.is_file():
                raise FileStorageError(f"Stored file '{uploaded_file.file_path}' does not exist.")

            parse_result = await parse_uploaded_file(uploaded_file.file_type, str(resolved_file_path))
        except Exception as exc:
            await self._update_parse_state(
                uploaded_file,
                parse_status=FileParseStatus.FAILED,
                parsed_content=self._build_parse_failure_content(uploaded_file.file_type, exc),
            )
            logger.exception("Failed to parse file {} for project {}", file_id, project_id)
            raise FileParsingError(project_id, file_id) from exc

        await self._update_parse_state(
            uploaded_file,
            parse_status=FileParseStatus.PARSED,
            parsed_content=parse_result.model_dump(mode="json"),
        )
        logger.info("Parsed file {} for project {}", file_id, project_id)
        return uploaded_file

    async def get_parsed_file(self, project_id: str, file_id: str) -> UploadedFile:
        await self._ensure_project_exists(project_id)
        return await self._get_uploaded_file_or_raise(project_id, file_id)

    async def _ensure_project_exists(self, project_id: str) -> None:
        stmt = select(Project.id).where(Project.id == project_id)
        project_id_in_db = (await self.session.execute(stmt)).scalar_one_or_none()
        if project_id_in_db is None:
            raise ProjectNotFoundError(project_id)

    async def _get_uploaded_file_or_raise(self, project_id: str, file_id: str) -> UploadedFile:
        stmt: Select[tuple[UploadedFile]] = select(UploadedFile).where(
            UploadedFile.project_id == project_id,
            UploadedFile.id == file_id,
        )
        uploaded_file = (await self.session.execute(stmt)).scalar_one_or_none()
        if uploaded_file is None:
            raise UploadedFileNotFoundError(project_id, file_id)
        return uploaded_file

    async def _write_upload_to_disk(self, upload_file: UploadFile, target_path: Path) -> int:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        bytes_written = 0

        try:
            async with aiofiles.open(target_path, "wb") as file_handle:
                while True:
                    chunk = await upload_file.read(self.CHUNK_SIZE_BYTES)
                    if not chunk:
                        break

                    bytes_written += len(chunk)
                    if bytes_written > self.MAX_FILE_SIZE_BYTES:
                        raise FileTooLargeError(
                            f"File '{self._normalize_original_name(getattr(upload_file, 'filename', None))}' "
                            f"exceeds the 50 MB upload limit."
                        )

                    await file_handle.write(chunk)
        except FileServiceError:
            raise
        except OSError as exc:
            raise FileStorageError(f"Failed to write uploaded file to '{target_path}'.") from exc

        return bytes_written

    def _normalize_original_name(self, filename: str | None) -> str:
        normalized = Path(filename or "").name.strip()
        if not normalized:
            raise FileValidationError("Uploaded file must include a valid filename.")
        return normalized

    def _extract_file_type(self, filename: str) -> str:
        suffix = Path(filename).suffix.strip().lower().lstrip(".")
        if not suffix:
            raise UnsupportedFileTypeError(
                f"File '{filename}' does not include a supported extension. "
                f"Allowed types: {', '.join(self.ALLOWED_FILE_TYPES)}."
            )
        if suffix not in self.ALLOWED_FILE_TYPES:
            raise UnsupportedFileTypeError(
                f"File type '.{suffix}' is not supported. "
                f"Allowed types: {', '.join(self.ALLOWED_FILE_TYPES)}."
            )
        return suffix

    def _project_root(self) -> Path:
        return self.settings.projects_dir.resolve()

    def _validated_project_dir(self, project_id: str) -> Path:
        project_root = self._project_root()
        project_dir = self.settings.project_dir(project_id).resolve()
        if not project_dir.is_relative_to(project_root):
            raise FileStorageError(f"Unsafe project path resolved for '{project_id}'.")
        if project_dir.parent != project_root or project_dir.name != project_id:
            raise FileStorageError(f"Refusing to operate on unexpected project path '{project_dir}'.")
        return project_dir

    def _uploads_dir(self, project_id: str) -> Path:
        project_dir = self._validated_project_dir(project_id)
        uploads_dir = (project_dir / "uploads").resolve()
        if not uploads_dir.is_relative_to(project_dir):
            raise FileStorageError(f"Unsafe uploads path resolved for '{project_id}'.")
        return uploads_dir

    def _resolve_project_file_path(self, project_id: str, relative_file_path: Path) -> Path:
        project_dir = self._validated_project_dir(project_id)
        uploads_dir = self._uploads_dir(project_id)
        resolved_path = (project_dir / relative_file_path).resolve()
        if not resolved_path.is_relative_to(uploads_dir):
            raise FileStorageError(f"Refusing to write outside uploads directory for project '{project_id}'.")
        return resolved_path

    def _resolve_stored_file_path(self, project_id: str, stored_file_path: str) -> Path:
        project_dir = self._validated_project_dir(project_id)
        uploads_dir = self._uploads_dir(project_id)
        candidate_path = Path(stored_file_path)
        resolved_path = (
            candidate_path.resolve()
            if candidate_path.is_absolute()
            else (project_dir / candidate_path).resolve()
        )
        if not resolved_path.is_relative_to(uploads_dir):
            raise FileStorageError(f"Refusing to access unsafe file path '{stored_file_path}'.")
        return resolved_path

    async def _remove_file_if_exists(self, target_path: Path) -> None:
        await asyncio.to_thread(self._unlink_if_exists, target_path)

    def _unlink_if_exists(self, target_path: Path) -> None:
        target_path.unlink(missing_ok=True)

    async def _update_parse_state(
        self,
        uploaded_file: UploadedFile,
        *,
        parse_status: FileParseStatus,
        parsed_content: dict | None,
    ) -> None:
        uploaded_file.parse_status = parse_status
        uploaded_file.parsed_content = parsed_content

        try:
            await self.session.commit()
            await self.session.refresh(uploaded_file)
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise FileStorageError(
                f"Failed to update parse state for uploaded file '{uploaded_file.id}'.",
            ) from exc

    def _build_parse_failure_content(self, file_type: str, exc: Exception) -> dict[str, object]:
        error_message = str(exc) or exc.__class__.__name__
        return {
            "file_type": file_type,
            "summary": f"Failed to parse file: {error_message}",
            "text_content": "",
            "structured_data": {
                "error": {
                    "type": exc.__class__.__name__,
                    "message": error_message,
                }
            },
            "key_points": [
                "Parsing failed",
                error_message,
            ],
        }
