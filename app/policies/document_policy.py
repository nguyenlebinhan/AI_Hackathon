from app.core.permissions import Permission, UserRole, role_has_permission
from app.model.documents import Document, DocumentApprovalStatus
from app.model.users import User, UserStatus


class DocumentPolicy:
    @staticmethod
    def can_read(
        actor: User,
        document: Document,
        *,
        has_explicit_access: bool,
    ) -> bool:
        if (
            not actor.is_active
            or actor.status != UserStatus.ACTIVE
            or document.commune_id != actor.commune_id
            or document.is_deleted
        ):
            return False
        if actor.role == UserRole.ADMIN:
            return role_has_permission(actor.role, Permission.DOCUMENTS_READ_COMMUNE)
        return actor.role == UserRole.USER and (
            (
                document.owner_id == actor.id
                and role_has_permission(actor.role, Permission.DOCUMENTS_READ_OWN)
            )
            or (
                has_explicit_access
                and role_has_permission(actor.role, Permission.DOCUMENTS_READ_GRANTED)
            )
        )

    @staticmethod
    def can_delete(actor: User, document: Document) -> bool:
        if (
            not actor.is_active
            or actor.status != UserStatus.ACTIVE
            or document.commune_id != actor.commune_id
            or document.is_deleted
            or document.deleted_at is not None
        ):
            return False
        if actor.role == UserRole.ADMIN:
            return role_has_permission(actor.role, Permission.DOCUMENTS_DELETE_COMMUNE)
        return (
            actor.role == UserRole.USER
            and role_has_permission(actor.role, Permission.DOCUMENTS_DELETE_OWN)
            and document.owner_id == actor.id
            and document.meeting_id is None
            and document.approval_status
            not in {
                DocumentApprovalStatus.APPROVED,
                DocumentApprovalStatus.PENDING_APPROVAL,
            }
        )

    @staticmethod
    def delete_denial_reason(actor: User, document: Document) -> str:
        if document.commune_id != actor.commune_id:
            return "TENANT_MISMATCH"
        if document.is_deleted or document.deleted_at is not None:
            return "ALREADY_DELETED"
        if actor.role == UserRole.USER and document.owner_id != actor.id:
            return "NOT_OWNER"
        if actor.role == UserRole.USER and document.meeting_id is not None:
            return "DOCUMENT_IN_MEETING"
        if actor.role == UserRole.USER and document.approval_status in {
            DocumentApprovalStatus.APPROVED,
            DocumentApprovalStatus.PENDING_APPROVAL,
        }:
            return "APPROVAL_STATE_FORBIDS_DELETE"
        return "MISSING_PERMISSION"

    @staticmethod
    def can_restore(actor: User, document: Document) -> bool:
        return (
            actor.is_active
            and actor.status == UserStatus.ACTIVE
            and actor.role == UserRole.ADMIN
            and role_has_permission(actor.role, Permission.DOCUMENTS_RESTORE_COMMUNE)
            and document.commune_id == actor.commune_id
            and document.is_deleted
            and document.deleted_at is not None
        )
