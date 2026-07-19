from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.documents import get_or_create_personal_workspace
from app.common.contracts import ApiSuccessResponse
from app.config.database import get_db
from app.core.permissions import Permission
from app.dependencies.permissions import require_permission
from app.documents.router import get_document_service
from app.exceptions import NotFoundError
from app.model.documents import Document
from app.model.users import User
from app.regulatory_change.schemas import (
    AnalyzeData,
    AnalyzeRequest,
    ChangeData,
    RegulatoryDocumentData,
    RegulatoryUploadData,
    RegulatoryUploadDetails,
    RegulatoryUploadMetadata,
    TimelineEntry,
)
from app.regulatory_change.service import RegulatoryChangeService
from app.service.documents import DocumentService

router = APIRouter(prefix="/regulatory", tags=["Secure regulatory change intelligence"])


def parse_upload_details(
    metadata: Annotated[str, Form(description="Regulatory metadata as a JSON object")],
) -> RegulatoryUploadDetails:
    try:
        return RegulatoryUploadDetails.model_validate_json(metadata)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc


def _owned_regulatory_document(
    document_id: str,
    actor: User,
    session: Session,
) -> None:
    document = session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == actor.id,
            Document.commune_id == actor.commune_id,
            Document.is_deleted.is_(False),
            Document.deleted_at.is_(None),
        )
    )
    if document is None:
        raise NotFoundError("REGULATORY_DOCUMENT_PROFILE", document_id)

    service = RegulatoryChangeService(session)
    if service.repository.version_by_document(document_id) is None:
        raise NotFoundError("REGULATORY_DOCUMENT_PROFILE", document_id)


@router.post(
    "/documents",
    response_model=ApiSuccessResponse[RegulatoryUploadData],
    status_code=status.HTTP_201_CREATED,
)
def upload_regulatory_document(
    file: Annotated[UploadFile, File(description="PDF or DOCX")],
    metadata: Annotated[RegulatoryUploadDetails, Depends(parse_upload_details)],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_CREATE))],
    session: Annotated[Session, Depends(get_db)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> ApiSuccessResponse[RegulatoryUploadData]:
    workspace = get_or_create_personal_workspace(session, actor)
    complete_metadata = RegulatoryUploadMetadata(
        workspace_id=workspace.id,
        **metadata.model_dump(),
    )
    data = RegulatoryChangeService(session).upload(
        file,
        complete_metadata,
        document_service,
        uploaded_by=actor.id,
        commune_id=actor.commune_id,
        owner_id=actor.id,
    )
    return ApiSuccessResponse(data=data, message="Đã tiếp nhận văn bản pháp lý")


@router.get(
    "/documents",
    response_model=ApiSuccessResponse[list[RegulatoryDocumentData]],
)
def list_regulatory_documents(
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[list[RegulatoryDocumentData]]:
    data = RegulatoryChangeService(session).list_documents(
        owner_id=actor.id,
        commune_id=actor.commune_id,
    )
    return ApiSuccessResponse(data=data)


@router.get(
    "/documents/{documentId}",
    response_model=ApiSuccessResponse[RegulatoryDocumentData],
)
def get_regulatory_profile(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[RegulatoryDocumentData]:
    _owned_regulatory_document(document_id, actor, session)
    return ApiSuccessResponse(data=RegulatoryChangeService(session).profile(document_id))


@router.get(
    "/documents/{documentId}/summary",
    response_model=ApiSuccessResponse[dict[str, Any]],
)
def get_regulatory_summary(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[dict[str, Any]]:
    _owned_regulatory_document(document_id, actor, session)
    return ApiSuccessResponse(data=RegulatoryChangeService(session).summary(document_id))


@router.get(
    "/documents/{documentId}/versions",
    response_model=ApiSuccessResponse[list[RegulatoryDocumentData]],
)
def get_regulatory_versions(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[list[RegulatoryDocumentData]]:
    _owned_regulatory_document(document_id, actor, session)
    return ApiSuccessResponse(data=RegulatoryChangeService(session).versions(document_id))


@router.get(
    "/documents/{documentId}/timeline",
    response_model=ApiSuccessResponse[list[TimelineEntry]],
)
def get_regulatory_timeline(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[list[TimelineEntry]]:
    _owned_regulatory_document(document_id, actor, session)
    return ApiSuccessResponse(data=RegulatoryChangeService(session).timeline(document_id))


@router.get(
    "/documents/{documentId}/changes",
    response_model=ApiSuccessResponse[list[ChangeData]],
)
def get_regulatory_changes(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[list[ChangeData]]:
    _owned_regulatory_document(document_id, actor, session)
    return ApiSuccessResponse(data=RegulatoryChangeService(session).changes(document_id))


@router.get(
    "/documents/{documentId}/legal-relations",
    response_model=ApiSuccessResponse[list[dict[str, Any]]],
)
def get_regulatory_legal_relations(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))],
    session: Annotated[Session, Depends(get_db)],
) -> ApiSuccessResponse[list[dict[str, Any]]]:
    _owned_regulatory_document(document_id, actor, session)
    return ApiSuccessResponse(data=RegulatoryChangeService(session).legal_relations(document_id))


@router.post(
    "/documents/{documentId}/analyze",
    response_model=ApiSuccessResponse[AnalyzeData],
)
def analyze_regulatory_document(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    actor: Annotated[User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))],
    session: Annotated[Session, Depends(get_db)],
    payload: AnalyzeRequest | None = None,
) -> ApiSuccessResponse[AnalyzeData]:
    _owned_regulatory_document(document_id, actor, session)
    data = RegulatoryChangeService(session).analyze(
        document_id,
        force=payload.force if payload else False,
    )
    return ApiSuccessResponse(data=data, message="Đã hoàn thành phân tích thay đổi")
