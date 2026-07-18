from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, RequestMetadata, record_audit
from app.core.permissions import Permission, UserRole, role_has_permission
from app.exceptions import AuthorizationError, NotFoundError
from app.model.documents import Document
from app.model.security import AuditResult
from app.model.users import User
from app.policies.document_policy import DocumentPolicy
from app.repositories.document_repository import DocumentRepository


class SecureDocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.documents = DocumentRepository(session)

    async def list_visible(
        self,
        *,
        actor: User,
        offset: int,
        limit: int,
    ) -> list[Document]:
        read_permission = (
            Permission.DOCUMENTS_READ_COMMUNE
            if actor.role == UserRole.ADMIN
            else Permission.DOCUMENTS_READ_OWN
        )
        if not role_has_permission(actor.role, read_permission):
            raise AuthorizationError()
        return await self.documents.list_visible(actor=actor, offset=offset, limit=limit)

    async def get_visible(
        self,
        *,
        actor: User,
        document_id: str,
        request: RequestMetadata,
    ) -> Document:
        document = await self.documents.get_active_by_id_and_commune(
            document_id=document_id,
            commune_id=actor.commune_id,
        )
        if document is None:
            await self._audit_not_found(actor, document_id, AuditAction.DOCUMENT_READ, request)
            raise NotFoundError("DOCUMENT", document_id)
        explicit_access = False
        if document.owner_id != actor.id:
            explicit_access = await self.documents.user_has_read_access(
                document_id=document.id,
                commune_id=actor.commune_id,
                user_id=actor.id,
            )
        if not DocumentPolicy.can_read(
            actor,
            document,
            has_explicit_access=explicit_access,
        ):
            record_audit(
                self.session,
                actor=actor,
                action=AuditAction.DOCUMENT_READ,
                result=AuditResult.DENIED,
                request=request,
                resource_type="DOCUMENT",
                resource_id=document_id,
                reason="NOT_FOUND_OR_NOT_GRANTED",
            )
            await self.session.commit()
            raise NotFoundError("DOCUMENT", document_id)
        record_audit(
            self.session,
            actor=actor,
            action=AuditAction.DOCUMENT_READ,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="DOCUMENT",
            resource_id=document.id,
        )
        await self.session.commit()
        return document

    async def soft_delete(
        self,
        *,
        actor: User,
        document_id: str,
        request: RequestMetadata,
    ) -> None:
        document = await self.documents.get_active_by_id_and_commune(
            document_id=document_id,
            commune_id=actor.commune_id,
            for_update=True,
        )
        if document is None:
            await self._audit_not_found(
                actor, document_id, AuditAction.DOCUMENT_DELETE, request
            )
            raise NotFoundError("DOCUMENT", document_id)
        if not DocumentPolicy.can_delete(actor, document):
            record_audit(
                self.session,
                actor=actor,
                action=AuditAction.DOCUMENT_DELETE,
                result=AuditResult.DENIED,
                request=request,
                resource_type="DOCUMENT",
                resource_id=document.id,
                reason=DocumentPolicy.delete_denial_reason(actor, document),
            )
            await self.session.commit()
            raise AuthorizationError(
                code="DOCUMENT_DELETE_FORBIDDEN",
                message="Trạng thái hoặc quyền sở hữu không cho phép xóa tài liệu.",
            )

        now = datetime.now(UTC)
        document.is_deleted = True
        document.deleted_at = now
        document.deleted_by = actor.id
        document.updated_at = now
        record_audit(
            self.session,
            actor=actor,
            action=AuditAction.DOCUMENT_DELETE,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="DOCUMENT",
            resource_id=document.id,
            metadata={"softDelete": True},
        )
        await self.session.commit()

    async def restore(
        self,
        *,
        actor: User,
        document_id: str,
        request: RequestMetadata,
    ) -> Document:
        document = await self.documents.get_deleted_by_id_and_commune(
            document_id=document_id,
            commune_id=actor.commune_id,
            for_update=True,
        )
        if document is None:
            await self._audit_not_found(
                actor, document_id, AuditAction.DOCUMENT_RESTORE, request
            )
            raise NotFoundError("DOCUMENT", document_id)
        if not DocumentPolicy.can_restore(actor, document):
            record_audit(
                self.session,
                actor=actor,
                action=AuditAction.DOCUMENT_RESTORE,
                result=AuditResult.DENIED,
                request=request,
                resource_type="DOCUMENT",
                resource_id=document.id,
                reason="MISSING_PERMISSION",
            )
            await self.session.commit()
            raise AuthorizationError()
        document.is_deleted = False
        document.deleted_at = None
        document.deleted_by = None
        document.updated_at = datetime.now(UTC)
        record_audit(
            self.session,
            actor=actor,
            action=AuditAction.DOCUMENT_RESTORE,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="DOCUMENT",
            resource_id=document.id,
        )
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def _audit_not_found(
        self,
        actor: User,
        document_id: str,
        action: AuditAction,
        request: RequestMetadata,
    ) -> None:
        record_audit(
            self.session,
            actor=actor,
            action=action,
            result=AuditResult.DENIED,
            request=request,
            resource_type="DOCUMENT",
            resource_id=document_id,
            reason="NOT_FOUND_OR_TENANT_MISMATCH",
        )
        await self.session.commit()
