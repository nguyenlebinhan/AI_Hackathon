from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config.settings import Settings
from app.core.permissions import UserRole

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65_536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
_REFRESH_PATTERN = re.compile(
    r"^v1\.(?P<session>[0-9a-fA-F-]{36})\.(?P<secret>[A-Za-z0-9_-]{43,128})$"
)


def hash_password(password: str) -> str:
    validate_password_strength(password)
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def validate_password_strength(password: str) -> None:
    if len(password) < 12:
        raise ValueError("Mật khẩu phải có ít nhất 12 ký tự.")
    if len(password.encode("utf-8")) > 1024:
        raise ValueError("Mật khẩu vượt quá độ dài cho phép.")
    if password.casefold() in {
        "password123!",
        "123456789012",
        "qwertyuiop12",
        "administrator",
    }:
        raise ValueError("Mật khẩu nằm trong danh sách quá phổ biến.")
    character_groups = (
        any(char.islower() for char in password),
        any(char.isupper() for char in password),
        any(char.isdigit() for char in password),
        any(not char.isalnum() for char in password),
    )
    if sum(character_groups) < 3:
        raise ValueError("Mật khẩu phải dùng ít nhất ba nhóm ký tự.")


def create_access_token(
    *,
    user_id: str,
    role: UserRole,
    commune_id: str,
    session_id: str,
    token_version: int,
    settings: Settings,
    now: datetime | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    issued_at = (now or datetime.now(UTC)).astimezone(UTC)
    expires_at = issued_at + (
        expires_delta or timedelta(minutes=settings.access_token_ttl_minutes)
    )
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role.value,
        "commune_id": commune_id,
        "session_id": session_id,
        "token_version": token_version,
        "type": "access",
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
        headers={"kid": settings.jwt_key_id, "typ": "JWT"},
    )


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={
            "require": [
                "sub",
                "role",
                "commune_id",
                "session_id",
                "token_version",
                "type",
                "iat",
                "exp",
                "jti",
                "iss",
                "aud",
            ]
        },
    )


def create_refresh_token(session_id: str) -> str:
    # The session UUID is a non-secret selector; the 256-bit random suffix is
    # the bearer credential. Neither role nor tenant data is embedded.
    UUID(session_id)
    return f"v1.{session_id}.{secrets.token_urlsafe(32)}"


def parse_refresh_token(token: str) -> str:
    match = _REFRESH_PATTERN.fullmatch(token)
    if match is None:
        raise ValueError("Malformed refresh token")
    session_id = match.group("session")
    UUID(session_id)
    return session_id


def hash_refresh_token(token: str, pepper: str) -> str:
    return hmac.new(
        pepper.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def refresh_hash_matches(candidate_hash: str, expected_hash: str) -> bool:
    return hmac.compare_digest(candidate_hash, expected_hash)


def identifier_fingerprint(identifier: str, pepper: str) -> str:
    return hmac.new(
        pepper.encode("utf-8"),
        identifier.strip().casefold().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:24]
