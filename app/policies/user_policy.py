from app.core.permissions import Permission, UserRole, role_has_permission
from app.model.users import User, UserStatus


class UserPolicy:
    @staticmethod
    def _is_active(actor: User) -> bool:
        return actor.is_active and actor.status == UserStatus.ACTIVE

    @staticmethod
    def can_create_user(actor: User) -> bool:
        return (
            UserPolicy._is_active(actor)
            and actor.role == UserRole.ADMIN
            and role_has_permission(actor.role, Permission.USERS_CREATE)
        )

    @staticmethod
    def can_read_commune_users(actor: User) -> bool:
        return (
            UserPolicy._is_active(actor)
            and actor.role == UserRole.ADMIN
            and role_has_permission(actor.role, Permission.USERS_READ_COMMUNE)
        )

    @staticmethod
    def can_read_province_directory(actor: User) -> bool:
        return (
            UserPolicy._is_active(actor)
            and actor.role == UserRole.ADMIN
            and role_has_permission(actor.role, Permission.STAFF_DIRECTORY_READ_PROVINCE)
        )

    @staticmethod
    def can_manage_target(actor: User, target: User, permission: Permission) -> bool:
        return (
            UserPolicy._is_active(actor)
            and actor.role == UserRole.ADMIN
            and role_has_permission(actor.role, permission)
            and actor.commune_id == target.commune_id
        )
