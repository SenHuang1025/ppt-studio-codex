from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db_session
from app.schemas import (
    FileParseStatus,
    ParsedFileResponse,
    UploadedFileDeleteResponse,
    UploadedFileListResponse,
    UploadedFileResponse,
)
from app.services import (
    FileParsingError,
    FileService,
    FileStorageError,
    FileTooLargeError,
    FileValidationError,
    ProjectNotFoundError,
    UnsupportedFileTypeError,
    UploadedFileNotFoundError,
)

router = APIRouter(prefix="/api/projects/{project_id}/files", tags=["files"])


def get_file_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> FileService:
    return FileService(session=session, settings=settings)


def _raise_file_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (ProjectNotFoundError, UploadedFileNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, FileTooLargeError):
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    if isinstance(exc, (UnsupportedFileTypeError, FileValidationError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, FileParsingError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    if isinstance(exc, FileStorageError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=UploadedFileListResponse)
async def list_project_files(
    project_id: str,
    file_service: FileService = Depends(get_file_service),
) -> UploadedFileListResponse:
    try:
        files = await file_service.list_files(project_id)
    except Exception as exc:
        _raise_file_http_error(exc)

    return UploadedFileListResponse(files=files)


@router.post("", response_model=UploadedFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(...),
    file_service: FileService = Depends(get_file_service),
) -> UploadedFileResponse:
    try:
        return await file_service.upload_file(project_id, file)
    except Exception as exc:
        _raise_file_http_error(exc)


@router.delete("/{file_id}", response_model=UploadedFileDeleteResponse)
async def delete_project_file(
    project_id: str,
    file_id: str,
    file_service: FileService = Depends(get_file_service),
) -> UploadedFileDeleteResponse:
    try:
        await file_service.delete_file(project_id, file_id)
    except Exception as exc:
        _raise_file_http_error(exc)

    return UploadedFileDeleteResponse(success=True)


@router.get("/{file_id}/parsed", response_model=ParsedFileResponse)
async def get_project_file_parsed(
    project_id: str,
    file_id: str,
    file_service: FileService = Depends(get_file_service),
) -> ParsedFileResponse:
    try:
        uploaded_file = await file_service.get_parsed_file(project_id, file_id)
        needs_lazy_parse = uploaded_file.parse_status == FileParseStatus.PENDING or (
            uploaded_file.parse_status == FileParseStatus.PARSED and uploaded_file.parsed_content is None
        )
        if needs_lazy_parse:
            try:
                uploaded_file = await file_service.parse_file(project_id, file_id)
            except FileParsingError:
                uploaded_file = await file_service.get_parsed_file(project_id, file_id)
    except Exception as exc:
        _raise_file_http_error(exc)

    return ParsedFileResponse(
        file_id=uploaded_file.id,
        parsed_content=uploaded_file.parsed_content,
        status=uploaded_file.parse_status,
    )
