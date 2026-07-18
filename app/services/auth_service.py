from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.core.audit import AuditAction, RequestMetadata, record_audit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    identifier_fingerprint,
    parse_refresh_token,
    password_needs_rehash,
    refresh_hash_matches,
    validate_password_strength,
    verify_password,
)
from app.core.time import ensure_utc
from app.exceptions import (
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)
from app.model.security import AuditResult, AuthSession, SessionRevokeReason
from app.model.users import User, UserStatus
from app.repositories.session_repository import AuthSessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenPairResponse,
)

_DUMMY_PASSWORD_HASH: str | None = None


async def _dummy_password_hash() -> str:
    global _DUMMY_PASSWORD_HASH
    if _DUMMY_PASSWORD_HASH is None:
        _DUMMY_PASSWORD_HASH = await to_thread.run_sync(
            hash_password, "Dummy-Password-Only-For-Timing-42!"
        )
    return _DUMMY_PASSWORD_HASH


async def _verify_password(password: str, password_hash: str) -> bool:
    return await to_thread.run_sync(verify_password, password, password_hash)


async def _hash_password(password: str) -> str:
    return await to_thread.run_sync(hash_password, password)


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.sessions = AuthSessionRepository(session)
        self.pepper = settings.refresh_token_pepper.get_secret_value()

    async def login(
        self,
        payload: LoginRequest,
        *,
        request: RequestMetadata,
    ) -> TokenPairResponse:
        now = datetime.now(UTC)
        password = payload.password.get_secret_value()
        user = await self.users.get_by_identifier_for_login(
            payload.identifier,
            for_update=True,
        )
        if user is None:
            await _verify_password(password, await _dummy_password_hash())
            record_audit(
                self.session,
                action=AuditAction.AUTH_LOGIN,
                result=AuditResult.DENIED,
                request=request,
                resource_type="AUTH",
                reason="INVALID_CREDENTIALS",
                metadata={
                    "identifierFingerprint": identifier_fingerprint(
                        payload.identifier, self.pepper
                    )
                },
            )
            await self.session.commit()
            raise AuthenticationError()

        if user.locked_until is not None and ensure_utc(user.locked_until) > now:
            remaining = int((ensure_utc(user.locked_until) - now).total_seconds())
            record_audit(
                self.session,
                actor=user,
                action=AuditAction.AUTH_LOGIN,
                result=AuditResult.DENIED,
                request=request,
                resource_type="USER",
                resource_id=user.id,
                reason="RATE_LIMITED",
            )
            await self.session.commit()
            raise RateLimitError(remaining)

        if not user.is_active or user.status != UserStatus.ACTIVE:
            await _verify_password(password, user.password_hash)
            record_audit(
                self.session,
                actor=user,
                action=AuditAction.AUTH_LOGIN,
                result=AuditResult.DENIED,
                request=request,
                resource_type="USER",
                resource_id=user.id,
                reason="ACCOUNT_INACTIVE",
            )
            await self.session.commit()
            raise AuthenticationError()

        if not await _verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            limited = user.failed_login_attempts >= self.settings.login_max_failed_attempts
            if limited:
                user.locked_until = now + timedelta(minutes=self.settings.login_lock_minutes)
                user.failed_login_attempts = 0
            record_audit(
                self.session,
                actor=user,
                action=AuditAction.AUTH_LOGIN,
                result=AuditResult.DENIED,
                request=request,
                resource_type="USER",
                resource_id=user.id,
                reason="RATE_LIMITED" if limited else "INVALID_CREDENTIALS",
            )
            await self.session.commit()
            if limited:
                raise RateLimitError(self.settings.login_lock_minutes * 60)
            raise AuthenticationError()

        user.failed_login_attempts = 0
        user.locked_until = None
        if password_needs_rehash(user.password_hash):
            user.password_hash = await _hash_password(password)
            # Keep the access token created below aligned with the PostgreSQL
            # security-change trigger and invalidate pre-rehash sessions.
            user.token_version += 1

        session_id = str(uuid4())
        refresh_token = create_refresh_token(session_id)
        refresh_expires_at = now + timedelta(days=self.settings.refresh_token_ttl_days)
        auth_session = AuthSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token, self.pepper),
            token_family_id=str(uuid4()),
            device_name=payload.device_name,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            expires_at=refresh_expires_at,
            last_used_at=now,
        )
        self.sessions.add(auth_session)
        access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            commune_id=user.commune_id,
            session_id=session_id,
            token_version=user.token_version,
            settings=self.settings,
            now=now,
        )
        record_audit(
            self.session,
            actor=user,
            action=AuditAction.AUTH_LOGIN,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="AUTH_SESSION",
            resource_id=session_id,
        )
        await self.session.commit()
        return self._token_pair(
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_expires_at=refresh_expires_at,
            user=user,
        )

    async def refresh(
        self,
        payload: RefreshRequest,
        *,
        request: RequestMetadata,
    ) -> TokenPairResponse:
        presented_token = payload.refresh_token.get_secret_value()
        try:
            session_id = parse_refresh_token(presented_token)
        except ValueError as exc:
            record_audit(
                self.session,
                action=AuditAction.AUTH_REFRESH,
                result=AuditResult.DENIED,
                request=request,
                resource_type="AUTH_SESSION",
                reason="MALFORMED_REFRESH_TOKEN",
            )
            await self.session.commit()
            raise AuthenticationError() from exc

        auth_session = await self.sessions.get_by_id_for_refresh(session_id)
        if auth_session is None:
            record_audit(
                self.session,
                action=AuditAction.AUTH_REFRESH,
                result=AuditResult.DENIED,
                request=request,
                resource_type="AUTH_SESSION",
                resource_id=session_id,
                reason="SESSION_NOT_FOUND",
            )
            await self.session.commit()
            raise AuthenticationError()

        user = await self.users.get_by_id_for_auth(auth_session.user_id)
        if user is None:
            raise AuthenticationError()
        now = datetime.now(UTC)
        candidate_hash = hash_refresh_token(presented_token, self.pepper)

        if not refresh_hash_matches(candidate_hash, auth_session.refresh_token_hash):
            previous = await self.sessions.find_history(
                session_id=session_id,
                token_hash=candidate_hash,
            )
            if previous is not None:
                await self.sessions.revoke_family(
                    token_family_id=auth_session.token_family_id,
                    revoked_at=now,
                    reason=SessionRevokeReason.REFRESH_TOKEN_REUSE.value,
                )
                record_audit(
                    self.session,
                    actor=user,
                    action=AuditAction.AUTH_REFRESH_REUSE,
                    result=AuditResult.DENIED,
                    request=request,
                    resource_type="AUTH_SESSION",
                    resource_id=session_id,
                    reason="ROTATED_TOKEN_REUSED",
                )
                await self.session.commit()
                raise AuthenticationError(
                    code="REFRESH_TOKEN_REUSE_DETECTED",
                    message="Phiên đăng nhập đã bị thu hồi.",
                )
            record_audit(
                self.session,
                actor=user,
                action=AuditAction.AUTH_REFRESH,
                result=AuditResult.DENIED,
                request=request,
                resource_type="AUTH_SESSION",
                resource_id=session_id,
                reason="INVALID_REFRESH_TOKEN",
            )
            await self.session.commit()
            raise AuthenticationError()

        if (
            auth_session.revoked_at is not None
            or ensure_utc(auth_session.expires_at) <= now
            or not user.is_active
            or user.status != UserStatus.ACTIVE
        ):
            record_audit(
                self.session,
                actor=user,
                action=AuditAction.AUTH_REFRESH,
                result=AuditResult.DENIED,
                request=request,
                resource_type="AUTH_SESSION",
                resource_id=session_id,
                reason="SESSION_REVOKED_OR_EXPIRED",
            )
            await self.session.commit()
            raise AuthenticationError()

        new_refresh_token = create_refresh_token(session_id)
        self.sessions.add_rotated_history(
            session_id=session_id,
            token_hash=auth_session.refresh_token_hash,
            used_at=now,
        )
        auth_session.refresh_token_hash = hash_refresh_token(new_refresh_token, self.pepper)
        auth_session.last_used_at = now
        auth_session.ip_address = request.ip_address
        auth_session.user_agent = request.user_agent
        access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            commune_id=user.commune_id,
            session_id=session_id,
            token_version=user.token_version,
            settings=self.settings,
            now=now,
        )
        record_audit(
            self.session,
            actor=user,
            action=AuditAction.AUTH_REFRESH,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="AUTH_SESSION",
            resource_id=session_id,
        )
        await self.session.commit()
        return self._token_pair(
            access_token=access_token,
            refresh_token=new_refresh_token,
            refresh_expires_at=ensure_utc(auth_session.expires_at),
            user=user,
        )

    async def logout(
        self,
        *,
        actor: User,
        auth_session: AuthSession,
        request: RequestMetadata,
    ) -> None:
        now = datetime.now(UTC)
        if auth_session.revoked_at is None:
            auth_session.revoked_at = now
            auth_session.revoke_reason = SessionRevokeReason.LOGOUT.value
        record_audit(
            self.session,
            actor=actor,
            action=AuditAction.AUTH_LOGOUT,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="AUTH_SESSION",
            resource_id=auth_session.id,
        )
        await self.session.commit()

    async def logout_all(
        self,
        *,
        actor: User,
        request: RequestMetadata,
    ) -> None:
        now = datetime.now(UTC)
        actor.token_version += 1
        await self.sessions.revoke_user_sessions(
            user_id=actor.id,
            revoked_at=now,
            reason=SessionRevokeReason.LOGOUT_ALL.value,
        )
        record_audit(
            self.session,
            actor=actor,
            action=AuditAction.AUTH_LOGOUT_ALL,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="USER",
            resource_id=actor.id,
        )
        await self.session.commit()

    async def change_password(
        self,
        payload: ChangePasswordRequest,
        *,
        actor: User,
        request: RequestMetadata,
    ) -> None:
        locked_actor = await self.users.get_by_id_and_commune(
            user_id=actor.id,
            commune_id=actor.commune_id,
            for_update=True,
        )
        if locked_actor is None or not await _verify_password(
            payload.current_password.get_secret_value(), locked_actor.password_hash
        ):
            record_audit(
                self.session,
                actor=actor,
                action=AuditAction.AUTH_CHANGE_PASSWORD,
                result=AuditResult.DENIED,
                request=request,
                resource_type="USER",
                resource_id=actor.id,
                reason="CURRENT_PASSWORD_INVALID",
            )
            await self.session.commit()
            raise BadRequestError(
                "CURRENT_PASSWORD_INVALID",
                "Mật khẩu hiện tại không chính xác.",
            )

        new_password = payload.new_password.get_secret_value()
        try:
            validate_password_strength(new_password)
        except ValueError as exc:
            raise BadRequestError("WEAK_PASSWORD", str(exc)) from exc
        if await _verify_password(new_password, locked_actor.password_hash):
            raise BadRequestError(
                "PASSWORD_REUSE",
                "Mật khẩu mới phải khác mật khẩu hiện tại.",
            )
        locked_actor.password_hash = await _hash_password(new_password)
        locked_actor.must_change_password = False
        locked_actor.token_version += 1
        now = datetime.now(UTC)
        await self.sessions.revoke_user_sessions(
            user_id=locked_actor.id,
            revoked_at=now,
            reason=SessionRevokeReason.PASSWORD_CHANGED.value,
        )
        record_audit(
            self.session,
            actor=locked_actor,
            action=AuditAction.AUTH_CHANGE_PASSWORD,
            result=AuditResult.SUCCESS,
            request=request,
            resource_type="USER",
            resource_id=locked_actor.id,
        )
        await self.session.commit()

    def _token_pair(
        self,
        *,
        access_token: str,
        refresh_token: str,
        refresh_expires_at: datetime,
        user: User,
    ) -> TokenPairResponse:
        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.settings.access_token_ttl_minutes * 60,
            refresh_expires_at=refresh_expires_at,
            must_change_password=user.must_change_password,
        )
