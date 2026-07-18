from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, RequestMetadata, record_audit
from app.exceptions import AuthorizationError, NotFoundError
from app.model.security import AuditLog, AuditResult
from app.model.users import User
from app.policies.audit_policy import AuditPolicy
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_logs = AuditRepository(session)

    async def list_commune(
        self,
        *,
        actor: User,
        offset: int,
        limit: int,
        request: RequestMetadata,
    ) -> list[AuditLog]:
        if not AuditPolicy.can_read_commune(actor):
            raise AuthorizationError()
        entries = await self.audit_logs.list_by_commune(
            commune_id=actor.commune_id,
            offset=offset,
            limit=limit,
        )
        record_audit(
            self.session,
            actor=actor,
            action=AuditAction.AUDIT_LOG_READ,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="AUDIT_LOG_COLLECTION",
            metadata={"offset": offset, "limit": limit},
        )
        await self.session.commit()
        return entries

    async def get_commune(
        self,
        *,
        actor: User,
        audit_log_id: str,
        request: RequestMetadata,
    ) -> AuditLog:
        if not AuditPolicy.can_read_commune(actor):
            raise AuthorizationError()
        entry = await self.audit_logs.get_by_id_and_commune(
            audit_log_id=audit_log_id,
            commune_id=actor.commune_id,
        )
        if entry is None:
            record_audit(
                self.session,
                actor=actor,
                action=AuditAction.AUDIT_LOG_READ,
                result=AuditResult.DENIED,
                request=request,
                resource_type="AUDIT_LOG",
                resource_id=audit_log_id,
                reason="NOT_FOUND_OR_TENANT_MISMATCH",
            )
            await self.session.commit()
            raise NotFoundError("AUDIT_LOG", audit_log_id)
        record_audit(
            self.session,
            actor=actor,
            action=AuditAction.AUDIT_LOG_READ,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="AUDIT_LOG",
            resource_id=entry.id,
        )
        await self.session.commit()
        return entry
