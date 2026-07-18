from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import Base, TimestampMixin


class SessionRevokeReason(StrEnum):
    LOGOUT = "LOGOUT"
    LOGOUT_ALL = "LOGOUT_ALL"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"
    ROLE_CHANGED = "ROLE_CHANGED"
    REFRESH_TOKEN_REUSE = "REFRESH_TOKEN_REUSE"
    EXPIRED = "EXPIRED"


class RefreshTokenHistoryStatus(StrEnum):
    ROTATED = "ROTATED"
    REVOKED = "REVOKED"


class AuditResult(StrEnum):
    SUCCESS = "SUCCESS"
    DENIED = "DENIED"
    FAILURE = "FAILURE"


class DocumentGrantPermission(StrEnum):
    READ = "READ"
    ASK = "ASK"


class AuthSession(TimestampMixin, Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint(
            "expires_at > created_at",
            name="auth_session_expiry_after_creation",
        ),
        Index("ix_auth_sessions_user_revoked", "user_id", "revoked_at"),
        Index("ix_auth_sessions_family", "token_family_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    token_family_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default=lambda: str(uuid4())
    )
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    revoke_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user = relationship("User", back_populates="auth_sessions")
    refresh_history: Mapped[list[RefreshTokenHistory]] = relationship(
        "RefreshTokenHistory",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RefreshTokenHistory(TimestampMixin, Base):
    __tablename__ = "refresh_token_history"
    __table_args__ = (
        Index("ix_refresh_history_session_status", "session_id", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("auth_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[RefreshTokenHistoryStatus] = mapped_column(
        SAEnum(
            RefreshTokenHistoryStatus,
            name="refresh_token_history_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session: Mapped[AuthSession] = relationship(
        "AuthSession", back_populates="refresh_history"
    )


class DocumentPermission(TimestampMixin, Base):
    __tablename__ = "document_permissions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "commune_id"],
            ["documents.id", "documents.commune_id"],
            ondelete="CASCADE",
            name="fk_document_permissions_document_tenant",
        ),
        ForeignKeyConstraint(
            ["user_id", "commune_id"],
            ["users.id", "users.commune_id"],
            ondelete="CASCADE",
            name="fk_document_permissions_user_tenant",
        ),
        UniqueConstraint(
            "document_id",
            "user_id",
            "permission",
            name="uq_document_permission_grant",
        ),
        Index("ix_document_permissions_user_commune", "user_id", "commune_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    document_id: Mapped[str] = mapped_column(String(40), nullable=False)
    user_id: Mapped[str] = mapped_column(String(40), nullable=False)
    commune_id: Mapped[str] = mapped_column(String(36), nullable=False)
    permission: Mapped[DocumentGrantPermission] = mapped_column(
        SAEnum(
            DocumentGrantPermission,
            name="document_grant_permission",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    granted_by: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_commune_created", "commune_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_actor_created", "actor_user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    commune_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("communes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[AuditResult] = mapped_column(
        SAEnum(
            AuditResult,
            name="audit_result",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


def _deny_audit_mutation(*_: Any, **__: Any) -> None:
    raise RuntimeError("audit_logs is append-only")


event.listen(AuditLog, "before_update", _deny_audit_mutation)
event.listen(AuditLog, "before_delete", _deny_audit_mutation)
