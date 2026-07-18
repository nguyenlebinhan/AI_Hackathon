from enum import StrEnum
from types import MappingProxyType


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"


class Permission(StrEnum):
    USERS_CREATE = "users:create"
    USERS_READ_COMMUNE = "users:read_commune"
    USERS_UPDATE_STATUS = "users:update_status"
    USERS_RESET_PASSWORD = "users:reset_password"

    STAFF_DIRECTORY_READ_PROVINCE = "staff_directory:read_province"

    DOCUMENTS_CREATE = "documents:create"
    DOCUMENTS_READ_OWN = "documents:read_own"
    DOCUMENTS_READ_GRANTED = "documents:read_granted"
    DOCUMENTS_READ_COMMUNE = "documents:read_commune"
    DOCUMENTS_DELETE_OWN = "documents:delete_own"
    DOCUMENTS_DELETE_COMMUNE = "documents:delete_commune"
    DOCUMENTS_RESTORE_COMMUNE = "documents:restore_commune"
    DOCUMENTS_ANALYZE_AI = "documents:analyze_ai"
    DOCUMENTS_ASK_AI = "documents:ask_ai"
    DOCUMENTS_READ_LEGAL_BASIS = "documents:read_legal_basis"

    AUDIT_LOGS_READ_COMMUNE = "audit_logs:read_commune"
    MEETINGS_READ_COMMUNE = "meetings:read_commune"
    MEETINGS_MANAGE_COMMUNE = "meetings:manage_commune"


_ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset(
        {
            Permission.USERS_CREATE,
            Permission.USERS_READ_COMMUNE,
            Permission.USERS_UPDATE_STATUS,
            Permission.USERS_RESET_PASSWORD,
            Permission.STAFF_DIRECTORY_READ_PROVINCE,
            Permission.DOCUMENTS_CREATE,
            Permission.DOCUMENTS_READ_OWN,
            Permission.DOCUMENTS_READ_GRANTED,
            Permission.DOCUMENTS_READ_COMMUNE,
            Permission.DOCUMENTS_DELETE_OWN,
            Permission.DOCUMENTS_DELETE_COMMUNE,
            Permission.DOCUMENTS_RESTORE_COMMUNE,
            Permission.DOCUMENTS_ANALYZE_AI,
            Permission.DOCUMENTS_ASK_AI,
            Permission.DOCUMENTS_READ_LEGAL_BASIS,
            Permission.AUDIT_LOGS_READ_COMMUNE,
            Permission.MEETINGS_READ_COMMUNE,
            Permission.MEETINGS_MANAGE_COMMUNE,
        }
    ),
    UserRole.USER: frozenset(
        {
            # A feature flag and document policy apply in addition to this grant.
            Permission.DOCUMENTS_CREATE,
            Permission.DOCUMENTS_READ_OWN,
            Permission.DOCUMENTS_READ_GRANTED,
            Permission.DOCUMENTS_DELETE_OWN,
            Permission.DOCUMENTS_ASK_AI,
            Permission.DOCUMENTS_READ_LEGAL_BASIS,
            Permission.MEETINGS_READ_COMMUNE,
        }
    ),
}

ROLE_PERMISSIONS = MappingProxyType(_ROLE_PERMISSIONS)


def role_has_permission(role: UserRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())

