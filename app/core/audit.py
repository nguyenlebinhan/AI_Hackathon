from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.security import AuditLog, AuditResult
from app.model.users import User


class AuditAction(StrEnum):
    AUTHORIZATION_DENIED = "authorization.denied"
    AUTH_LOGIN = "auth.login"
    AUTH_REFRESH = "auth.refresh"
    AUTH_REFRESH_REUSE = "auth.refresh_token_reuse"
    AUTH_LOGOUT = "auth.logout"
    AUTH_LOGOUT_ALL = "auth.logout_all"
    AUTH_CHANGE_PASSWORD = "auth.change_password"
    USER_CREATE = "users.create"
    USER_LOCK = "users.lock"
    USER_UNLOCK = "users.unlock"
    USER_RESET_PASSWORD = "users.reset_password"
    STAFF_DIRECTORY_READ = "staff_directory.read_province"
    DOCUMENT_READ = "documents.read"
    DOCUMENT_DELETE = "documents.delete"
    DOCUMENT_RESTORE = "documents.restore"
    AUDIT_LOG_READ = "audit_logs.read"


@dataclass(frozen=True, slots=True)
class RequestMetadata:
    ip_address: str | None
    user_agent: str | None
    request_id: str

    @classmethod
    def from_request(cls, request: Request) -> RequestMetadata:
        client = request.client
        return cls(
            ip_address=client.host[:45] if client is not None else None,
            user_agent=request.headers.get("user-agent", "")[:512] or None,
            request_id=str(getattr(request.state, "request_id", "missing-request-id"))[:128],
        )


_SENSITIVE_KEY_PARTS = {
    "password",
    "passwd",
    "token",
    "authorization",
    "cookie",
    "secret",
    "credential",
}


def sanitize_audit_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)[:128]
            folded = key.casefold()
            if any(part in folded for part in _SENSITIVE_KEY_PARTS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_audit_metadata(raw_value)
        return sanitized
    if isinstance(value, list):
        return [sanitize_audit_metadata(item) for item in value[:100]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value[:1024] if isinstance(value, str) else value
    return str(value)[:1024]


def record_audit(
    session: AsyncSession,
    *,
    action: AuditAction | str,
    result: AuditResult,
    request: RequestMetadata,
    actor: User | None = None,
    commune_id: str | None = None,
    resource_type: str,
    resource_id: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        commune_id=commune_id if commune_id is not None else getattr(actor, "commune_id", None),
        actor_user_id=getattr(actor, "id", None),
        action=str(action),
        resource_type=resource_type[:64],
        resource_id=resource_id[:64] if resource_id else None,
        result=result,
        reason=reason[:255] if reason else None,
        ip_address=request.ip_address,
        user_agent=request.user_agent,
        request_id=request.request_id,
        metadata_json=sanitize_audit_metadata(metadata or {}),
    )
    session.add(entry)
    return entry
