from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import RequestMetadata
from app.core.permissions import Permission
from app.database.async_session import get_async_db
from app.dependencies.permissions import require_permission
from app.model.users import User
from app.schemas.audit_log import AuditLogPublic, audit_to_public
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin/audit-logs", tags=["Admin audit logs"])


@router.get("", response_model=list[AuditLogPublic])
async def list_audit_logs(
    request: Request,
    actor: Annotated[
        User, Depends(require_permission(Permission.AUDIT_LOGS_READ_COMMUNE))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AuditLogPublic]:
    entries = await AuditService(session).list_commune(
        actor=actor,
        offset=offset,
        limit=limit,
        request=RequestMetadata.from_request(request),
    )
    return [audit_to_public(entry) for entry in entries]


@router.get("/{audit_log_id}", response_model=AuditLogPublic)
async def get_audit_log(
    audit_log_id: Annotated[str, Path(min_length=1, max_length=40)],
    request: Request,
    actor: Annotated[
        User, Depends(require_permission(Permission.AUDIT_LOGS_READ_COMMUNE))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> AuditLogPublic:
    entry = await AuditService(session).get_commune(
        actor=actor,
        audit_log_id=audit_log_id,
        request=RequestMetadata.from_request(request),
    )
    return audit_to_public(entry)

