from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Path, UploadFile, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import Settings, get_settings
from app.model.schemas.documents import (
    DocumentDeleteResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.model.schemas.processing import ProcessingStatusResponse
from app.service.documents import DocumentService
from app.service.storage import ObjectStorage
from app.utils.storage_dependencies import get_object_storage
from app.utils.task_dispatcher import TaskDispatcher, get_task_dispatcher

router = APIRouter(tags=["Documents"])


def get_document_service(
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    dispatcher: Annotated[TaskDispatcher, Depends(get_task_dispatcher)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentService:
    return DocumentService(
        session,
        storage=storage,
        dispatcher=dispatcher,
        settings=settings,
    )


@router.post(
    "/workspaces/{workspaceId}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    workspace_id: Annotated[
        str,
        Path(alias="workspaceId", min_length=4, max_length=40),
    ],
    file: Annotated[UploadFile, File(description="PDF or DOCX document")],
    service: Annotated[DocumentService, Depends(get_document_service)],
    display_name: Annotated[
        str | None,
        Form(alias="displayName", min_length=1, max_length=255),
    ] = None,
) -> DocumentUploadResponse:
    return service.upload(workspace_id, file, display_name=display_name)


@router.get(
    "/documents/{documentId}",
    response_model=DocumentResponse,
    response_model_exclude_none=True,
)
def get_document(
    document_id: Annotated[
        str,
        Path(alias="documentId", min_length=5, max_length=40),
    ],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    return service.get(document_id)


@router.get(
    "/documents/{documentId}/status",
    response_model=ProcessingStatusResponse,
    response_model_exclude_none=True,
)
def get_document_status(
    document_id: Annotated[
        str,
        Path(alias="documentId", min_length=5, max_length=40),
    ],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ProcessingStatusResponse:
    return service.get_status(document_id)


@router.delete(
    "/documents/{documentId}",
    response_model=DocumentDeleteResponse,
)
def delete_document(
    document_id: Annotated[
        str,
        Path(alias="documentId", min_length=5, max_length=40),
    ],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentDeleteResponse:
    return service.soft_delete(document_id)
