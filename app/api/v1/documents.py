from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import RequestMetadata
from app.core.permissions import Permission
from app.database.async_session import get_async_db
from app.dependencies.permissions import require_permission
from app.model.users import User
from app.schemas.document import DocumentPublic, document_to_public
from app.services.document_service import SecureDocumentService

router = APIRouter(prefix="/documents", tags=["Secure documents"])


@router.get("", response_model=list[DocumentPublic])
async def list_documents(
    actor: Annotated[
        User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[DocumentPublic]:
    documents = await SecureDocumentService(session).list_visible(
        actor=actor,
        offset=offset,
        limit=limit,
    )
    return [document_to_public(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentPublic)
async def get_document(
    document_id: Annotated[str, Path(min_length=1, max_length=40)],
    request: Request,
    actor: Annotated[
        User, Depends(require_permission(Permission.DOCUMENTS_READ_OWN))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> DocumentPublic:
    document = await SecureDocumentService(session).get_visible(
        actor=actor,
        document_id=document_id,
        request=RequestMetadata.from_request(request),
    )
    return document_to_public(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: Annotated[str, Path(min_length=1, max_length=40)],
    request: Request,
    actor: Annotated[
        User, Depends(require_permission(Permission.DOCUMENTS_DELETE_OWN))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> Response:
    await SecureDocumentService(session).soft_delete(
        actor=actor,
        document_id=document_id,
        request=RequestMetadata.from_request(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_id}/restore", response_model=DocumentPublic)
async def restore_document(
    document_id: Annotated[str, Path(min_length=1, max_length=40)],
    request: Request,
    actor: Annotated[
        User, Depends(require_permission(Permission.DOCUMENTS_RESTORE_COMMUNE))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> DocumentPublic:
    document = await SecureDocumentService(session).restore(
        actor=actor,
        document_id=document_id,
        request=RequestMetadata.from_request(request),
    )
    return document_to_public(document)

