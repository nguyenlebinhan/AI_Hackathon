from __future__ import annotations

from datetime import UTC, datetime

from anyio import to_thread
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, RequestMetadata, record_audit
from app.core.permissions import Permission, UserRole
from app.core.security import hash_password, validate_password_strength
from app.exceptions import (
    AuthorizationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
)
from app.model.security import AuditResult, SessionRevokeReason
from app.model.users import User, UserStatus
from app.policies.user_policy import UserPolicy
from app.repositories.session_repository import AuthSessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import AdminUserCreateRequest, StaffDirectoryEntry


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.sessions = AuthSessionRepository(session)

    async def create_user(
        self,
        payload: AdminUserCreateRequest,
        *,
        actor: User,
        request: RequestMetadata,
    ) -> User:
        if not UserPolicy.can_create_user(actor):
            raise AuthorizationError()
        password = payload.temporary_password.get_secret_value()
        try:
            validate_password_strength(password)
        except ValueError as exc:
            raise BadRequestError("WEAK_PASSWORD", str(exc)) from exc

        # Role, tenant and creator are server-owned fields. Commune admins can
        # create ordinary staff only; ADMIN provisioning is an out-of-band flow.
        user = User(
            commune_id=actor.commune_id,
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            position=payload.position,
            department=payload.department,
            role=UserRole.USER,
            password_hash=await to_thread.run_sync(hash_password, password),
            is_active=True,
            must_change_password=True,
            status=UserStatus.ACTIVE,
            created_by=actor.id,
        )
        self.users.add(user)
        try:
            await self.session.flush()
            record_audit(
                self.session,
                actor=actor,
                action=AuditAction.USER_CREATE,
                result=AuditResult.SUCCESS,
                request=request,
                resource_type="USER",
                resource_id=user.id,
            )
            await self.session.commit()
        except IntegrityError as exc:
            actor_id = actor.id
            actor_commune_id = actor.commune_id
            await self.session.rollback()
            reloaded_actor = await self.users.get_by_id_and_commune(
                user_id=actor_id,
                commune_id=actor_commune_id,
            )
            record_audit(
                self.session,
                actor=reloaded_actor,
                commune_id=actor_commune_id,
                action=AuditAction.USER_CREATE,
                result=AuditResult.DENIED,
                request=request,
                resource_type="USER",
                reason="USERNAME_OR_EMAIL_EXISTS",
            )
            await self.session.commit()
            raise ConflictError(
                "USERNAME_OR_EMAIL_EXISTS",
                "Username hoặc email đã tồn tại.",
            ) from exc
        await self.session.refresh(user)
        return user

    async def list_commune_users(
        self,
        *,
        actor: User,
        offset: int,
        limit: int,
    ) -> list[User]:
        if not UserPolicy.can_read_commune_users(actor):
            raise AuthorizationError()
        return await self.users.list_by_commune(
            commune_id=actor.commune_id,
            offset=offset,
            limit=limit,
        )

    async def get_commune_user(self, *, actor: User, target_user_id: str) -> User:
        target = await self.users.get_by_id_and_commune(
            user_id=target_user_id,
            commune_id=actor.commune_id,
        )
        if target is None:
            raise NotFoundError("USER", target_user_id)
        if not UserPolicy.can_manage_target(
            actor, target, Permission.USERS_READ_COMMUNE
        ):
            raise AuthorizationError()
        return target

    async def lock_user(
        self,
        *,
        actor: User,
        target_user_id: str,
        request: RequestMetadata,
    ) -> User:
        target = await self.users.get_by_id_and_commune(
            user_id=target_user_id,
            commune_id=actor.commune_id,
            for_update=True,
        )
        if target is None:
            await self._audit_missing_target(
                actor=actor,
                action=AuditAction.USER_LOCK,
                target_user_id=target_user_id,
                request=request,
            )
            raise NotFoundError("USER", target_user_id)
        if not UserPolicy.can_manage_target(
            actor, target, Permission.USERS_UPDATE_STATUS
        ):
            raise AuthorizationError()
        if target.id == actor.id:
            raise ConflictError("SELF_LOCK_FORBIDDEN", "Không thể tự khóa tài khoản.")
        if not target.is_active or target.status == UserStatus.LOCKED:
            raise ConflictError("USER_ALREADY_LOCKED", "Tài khoản đã bị khóa.")
        if (
            target.role == UserRole.ADMIN
            and await self.users.count_active_admins(actor.commune_id) <= 1
        ):
            raise ConflictError(
                "LAST_ADMIN_LOCK_FORBIDDEN",
                "Không thể khóa quản trị viên hoạt động cuối cùng của xã.",
            )

        now = datetime.now(UTC)
        target.is_active = False
        target.status = UserStatus.LOCKED
        target.locked_until = None
        target.token_version += 1
        await self.sessions.revoke_user_sessions(
            user_id=target.id,
            revoked_at=now,
            reason=SessionRevokeReason.ACCOUNT_LOCKED.value,
        )
        record_audit(
            self.session,
            actor=actor,
            action=AuditAction.USER_LOCK,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="USER",
            resource_id=target.id,
        )
        await self.session.commit()
        await self.session.refresh(target)
        return target

    async def unlock_user(
        self,
        *,
        actor: User,
        target_user_id: str,
        request: RequestMetadata,
    ) -> User:
        target = await self.users.get_by_id_and_commune(
            user_id=target_user_id,
            commune_id=actor.commune_id,
            for_update=True,
        )
        if target is None:
            await self._audit_missing_target(
                actor=actor,
                action=AuditAction.USER_UNLOCK,
                target_user_id=target_user_id,
                request=request,
            )
            raise NotFoundError("USER", target_user_id)
        if not UserPolicy.can_manage_target(
            actor, target, Permission.USERS_UPDATE_STATUS
        ):
            raise AuthorizationError()
        if target.is_active and target.status == UserStatus.ACTIVE:
            raise ConflictError("USER_ALREADY_ACTIVE", "Tài khoản đang hoạt động.")
        if target.status != UserStatus.LOCKED:
            raise ConflictError(
                "USER_NOT_MANUALLY_LOCKED",
                "Chỉ tài khoản bị khóa mới có thể mở khóa.",
            )
        target.is_active = True
        target.status = UserStatus.ACTIVE
        target.locked_until = None
        target.failed_login_attempts = 0
        record_audit(
            self.session,
            actor=actor,
            action=AuditAction.USER_UNLOCK,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="USER",
            resource_id=target.id,
        )
        await self.session.commit()
        await self.session.refresh(target)
        return target

    async def reset_password(
        self,
        *,
        actor: User,
        target_user_id: str,
        temporary_password: str,
        request: RequestMetadata,
    ) -> None:
        target = await self.users.get_by_id_and_commune(
            user_id=target_user_id,
            commune_id=actor.commune_id,
            for_update=True,
        )
        if target is None:
            await self._audit_missing_target(
                actor=actor,
                action=AuditAction.USER_RESET_PASSWORD,
                target_user_id=target_user_id,
                request=request,
            )
            raise NotFoundError("USER", target_user_id)
        if not UserPolicy.can_manage_target(
            actor, target, Permission.USERS_RESET_PASSWORD
        ):
            raise AuthorizationError()
        try:
            validate_password_strength(temporary_password)
        except ValueError as exc:
            raise BadRequestError("WEAK_PASSWORD", str(exc)) from exc
        target.password_hash = await to_thread.run_sync(
            hash_password, temporary_password
        )
        target.must_change_password = True
        target.token_version += 1
        now = datetime.now(UTC)
        await self.sessions.revoke_user_sessions(
            user_id=target.id,
            revoked_at=now,
            reason=SessionRevokeReason.PASSWORD_RESET.value,
        )
        record_audit(
            self.session,
            actor=actor,
            action=AuditAction.USER_RESET_PASSWORD,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="USER",
            resource_id=target.id,
        )
        await self.session.commit()

    async def province_directory(
        self,
        *,
        actor: User,
        offset: int,
        limit: int,
        request: RequestMetadata,
    ) -> list[StaffDirectoryEntry]:
        if not UserPolicy.can_read_province_directory(actor):
            raise AuthorizationError()
        rows = await self.users.list_directory_by_province(
            requester_commune_id=actor.commune_id,
            offset=offset,
            limit=limit,
        )
        record_audit(
            self.session,
            actor=actor,
            action=AuditAction.STAFF_DIRECTORY_READ,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="STAFF_DIRECTORY",
            metadata={"offset": offset, "limit": limit},
        )
        await self.session.commit()
        return [StaffDirectoryEntry.model_validate(row) for row in rows]

    async def _audit_missing_target(
        self,
        *,
        actor: User,
        action: AuditAction,
        target_user_id: str,
        request: RequestMetadata,
    ) -> None:
        record_audit(
            self.session,
            actor=actor,
            action=action,
            result=AuditResult.DENIED,
            request=request,
            resource_type="USER",
            resource_id=target_user_id,
            reason="NOT_FOUND_OR_TENANT_MISMATCH",
        )
        await self.session.commit()
