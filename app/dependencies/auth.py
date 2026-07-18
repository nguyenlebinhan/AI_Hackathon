from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.core.security import decode_access_token
from app.core.time import ensure_utc
from app.database.async_session import get_async_db
from app.exceptions import AuthenticationError
from app.model.security import AuthSession
from app.model.users import User, UserStatus
from app.repositories.session_repository import AuthSessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AccessTokenClaims

bearer_scheme = HTTPBearer(
    scheme_name="VADS access token",
    description="Short-lived JWT access token",
    auto_error=False,
)


@dataclass(frozen=True, slots=True)
class AuthContext:
    user: User
    auth_session: AuthSession
    claims: AccessTokenClaims


async def get_auth_context(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthContext:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise AuthenticationError()
    try:
        raw_claims = decode_access_token(credentials.credentials, settings)
        claims = AccessTokenClaims.model_validate(raw_claims)
    except (jwt.PyJWTError, ValidationError, ValueError, TypeError) as exc:
        raise AuthenticationError() from exc

    user = await UserRepository(session).get_by_id_for_auth(claims.sub)
    if user is None:
        raise AuthenticationError()
    auth_session = await AuthSessionRepository(session).get_by_id_and_user(
        session_id=claims.session_id,
        user_id=user.id,
    )
    now = datetime.now(UTC)
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or ensure_utc(auth_session.expires_at) <= now
        or claims.token_version != user.token_version
        or claims.role != user.role
        or claims.commune_id != user.commune_id
    ):
        raise AuthenticationError()
    return AuthContext(user=user, auth_session=auth_session, claims=claims)


async def get_current_user(
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> User:
    return context.user


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_active or user.status != UserStatus.ACTIVE:
        # A locked account's bearer token is treated as invalid authentication,
        # not as a valid identity with insufficient authorization.
        raise AuthenticationError()
    return user
