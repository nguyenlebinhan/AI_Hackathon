from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, RequestMetadata, record_audit
from app.core.permissions import Permission, role_has_permission
from app.database.async_session import get_async_db
from app.dependencies.auth import get_current_active_user
from app.exceptions import AuthorizationError
from app.model.security import AuditResult
from app.model.users import User


def require_permission(
    permission: Permission,
) -> Callable[..., Coroutine[Any, Any, User]]:
    async def dependency(
        user: Annotated[User, Depends(get_current_active_user)],
        request: Request,
        session: Annotated[AsyncSession, Depends(get_async_db)],
    ) -> User:
        if user.must_change_password:
            record_audit(
                session,
                actor=user,
                action=AuditAction.AUTHORIZATION_DENIED,
                result=AuditResult.DENIED,
                request=RequestMetadata.from_request(request),
                resource_type="ENDPOINT",
                resource_id=request.url.path,
                reason="PASSWORD_CHANGE_REQUIRED",
                metadata={"requiredPermission": permission.value},
            )
            await session.commit()
            raise AuthorizationError(
                code="PASSWORD_CHANGE_REQUIRED",
                message="Bạn phải đổi mật khẩu trước khi tiếp tục.",
            )
        if not role_has_permission(user.role, permission):
            record_audit(
                session,
                actor=user,
                action=AuditAction.AUTHORIZATION_DENIED,
                result=AuditResult.DENIED,
                request=RequestMetadata.from_request(request),
                resource_type="ENDPOINT",
                resource_id=request.url.path,
                reason="MISSING_PERMISSION",
                metadata={"requiredPermission": permission.value},
            )
            await session.commit()
            raise AuthorizationError(
                code="MISSING_PERMISSION",
                message="Bạn không có quyền thực hiện thao tác này.",
            )
        return user

    return dependency
