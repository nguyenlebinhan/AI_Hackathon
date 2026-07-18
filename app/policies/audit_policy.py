from app.core.permissions import Permission, UserRole, role_has_permission
from app.model.users import User, UserStatus


class AuditPolicy:
    @staticmethod
    def can_read_commune(actor: User) -> bool:
        return (
            actor.role == UserRole.ADMIN
            and role_has_permission(actor.role, Permission.AUDIT_LOGS_READ_COMMUNE)
            and actor.is_active
            and actor.status == UserStatus.ACTIVE
        )
