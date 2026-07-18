from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import Settings, get_settings
from app.core.permissions import UserRole
from app.core.security import hash_password
from app.database.async_session import get_async_db
from app.main import create_app
from app.model.base import Base
from app.model.documents import Document, DocumentApprovalStatus
from app.model.processing import ProcessingStatus
from app.model.security import (
    AuditLog,
    AuditResult,
    DocumentGrantPermission,
    DocumentPermission,
)
from app.model.tenancy import Commune, Province
from app.model.users import User, UserStatus
from app.model.workspaces import Workspace
from app.utils.model_registry import import_models

TEST_PASSWORD = "Correct-Horse-Battery-42!"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def security_settings(test_settings: Settings, tmp_path: Path) -> Settings:
    return test_settings.model_copy(
        update={
            "legacy_api_enabled": False,
            "database_async_url": f"sqlite+aiosqlite:///{tmp_path / 'security.db'}",
            "jwt_secret_key": SecretStr("test-jwt-secret-that-is-longer-than-thirty-two-bytes"),
            "refresh_token_pepper": SecretStr(
                "test-refresh-pepper-that-is-different-and-long-enough"
            ),
            "access_token_ttl_minutes": 10,
            "refresh_token_ttl_days": 30,
            "login_max_failed_attempts": 5,
            "login_lock_minutes": 15,
            "user_document_upload_enabled": True,
        }
    )


@pytest.fixture
async def security_session_factory(
    security_settings: Settings,
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    import_models()
    engine = create_async_engine(security_settings.resolved_async_database_url)

    @event.listens_for(engine.sync_engine, "connect")
    def enable_sqlite_foreign_keys(
        dbapi_connection: Any,
        connection_record: Any,
    ) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )
    yield factory
    await engine.dispose()


@pytest.fixture
async def security_app(
    security_settings: Settings,
    security_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[FastAPI, None]:
    application = create_app(security_settings)

    async def override_async_db() -> AsyncGenerator[AsyncSession, None]:
        async with security_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    application.dependency_overrides[get_async_db] = override_async_db
    application.dependency_overrides[get_settings] = lambda: security_settings
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def async_client(security_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=security_app),
        base_url="http://testserver",
    ) as client:
        yield client


def _user(*, commune_id: str, username: str, role: UserRole) -> User:
    return User(
        id=str(uuid4()),
        commune_id=commune_id,
        username=username,
        email=f"{username}@example.gov.vn",
        full_name=f"Cán bộ {username}",
        position="Chuyên viên",
        department="Văn phòng",
        role=role,
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
        must_change_password=False,
        status=UserStatus.ACTIVE,
    )


def _document(
    *,
    workspace_id: str,
    commune_id: str,
    owner_id: str,
    name: str,
    approval_status: DocumentApprovalStatus = DocumentApprovalStatus.DRAFT,
    meeting_id: str | None = None,
    deleted: bool = False,
) -> Document:
    now = datetime.now(UTC)
    return Document(
        id=str(uuid4()),
        commune_id=commune_id,
        owner_id=owner_id,
        workspace_id=workspace_id,
        uploaded_by=owner_id,
        approval_status=approval_status,
        meeting_id=meeting_id,
        display_name=name,
        original_filename=f"{name}.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=100,
        checksum=uuid4().hex + uuid4().hex,
        status=ProcessingStatus.COMPLETED,
        is_deleted=deleted,
        deleted_at=now if deleted else None,
        deleted_by=owner_id if deleted else None,
    )


@pytest.fixture
async def security_data(
    security_session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, Any]:
    async with security_session_factory() as session:
        province = Province(id=str(uuid4()), name="Tỉnh Kiểm Thử", code="TEST")
        commune_a = Commune(
            id=str(uuid4()),
            province_id=province.id,
            name="Xã A",
            code="XA",
        )
        commune_b = Commune(
            id=str(uuid4()),
            province_id=province.id,
            name="Xã B",
            code="XB",
        )
        admin_a = _user(commune_id=commune_a.id, username="admin.a", role=UserRole.ADMIN)
        user_a = _user(commune_id=commune_a.id, username="user.a", role=UserRole.USER)
        admin_b = _user(commune_id=commune_b.id, username="admin.b", role=UserRole.ADMIN)
        user_b = _user(commune_id=commune_b.id, username="user.b", role=UserRole.USER)
        workspace_a = Workspace(id=str(uuid4()), name="Workspace A")
        workspace_b = Workspace(id=str(uuid4()), name="Workspace B")
        session.add_all(
            [
                province,
                commune_a,
                commune_b,
                admin_a,
                user_a,
                admin_b,
                user_b,
                workspace_a,
                workspace_b,
            ]
        )
        await session.flush()

        doc_own = _document(
            workspace_id=workspace_a.id,
            commune_id=commune_a.id,
            owner_id=user_a.id,
            name="Own draft",
        )
        doc_other = _document(
            workspace_id=workspace_a.id,
            commune_id=commune_a.id,
            owner_id=admin_a.id,
            name="Other draft",
        )
        doc_shared = _document(
            workspace_id=workspace_a.id,
            commune_id=commune_a.id,
            owner_id=admin_a.id,
            name="Shared draft",
        )
        doc_approved = _document(
            workspace_id=workspace_a.id,
            commune_id=commune_a.id,
            owner_id=user_a.id,
            name="Approved",
            approval_status=DocumentApprovalStatus.APPROVED,
        )
        doc_pending = _document(
            workspace_id=workspace_a.id,
            commune_id=commune_a.id,
            owner_id=user_a.id,
            name="Pending",
            approval_status=DocumentApprovalStatus.PENDING_APPROVAL,
        )
        doc_meeting = _document(
            workspace_id=workspace_a.id,
            commune_id=commune_a.id,
            owner_id=user_a.id,
            name="Meeting",
            meeting_id=str(uuid4()),
        )
        doc_deleted = _document(
            workspace_id=workspace_a.id,
            commune_id=commune_a.id,
            owner_id=user_a.id,
            name="Deleted",
            deleted=True,
        )
        doc_b = _document(
            workspace_id=workspace_b.id,
            commune_id=commune_b.id,
            owner_id=user_b.id,
            name="Commune B",
        )
        session.add_all(
            [
                doc_own,
                doc_other,
                doc_shared,
                doc_approved,
                doc_pending,
                doc_meeting,
                doc_deleted,
                doc_b,
            ]
        )
        await session.flush()
        session.add(
            DocumentPermission(
                document_id=doc_shared.id,
                user_id=user_a.id,
                commune_id=commune_a.id,
                permission=DocumentGrantPermission.READ,
                granted_by=admin_a.id,
            )
        )
        audit_b = AuditLog(
            commune_id=commune_b.id,
            actor_user_id=admin_b.id,
            action="seed.event",
            resource_type="TEST",
            result=AuditResult.SUCCESS,
            request_id=str(uuid4()),
            metadata_json={},
        )
        session.add(audit_b)
        await session.commit()
        return {
            "province": province,
            "commune_a": commune_a,
            "commune_b": commune_b,
            "admin_a": admin_a,
            "user_a": user_a,
            "admin_b": admin_b,
            "user_b": user_b,
            "doc_own": doc_own,
            "doc_other": doc_other,
            "doc_shared": doc_shared,
            "doc_approved": doc_approved,
            "doc_pending": doc_pending,
            "doc_meeting": doc_meeting,
            "doc_deleted": doc_deleted,
            "doc_b": doc_b,
            "audit_b": audit_b,
        }


async def login_as(client: AsyncClient, username: str) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": username,
            "password": TEST_PASSWORD,
            "device_name": "pytest",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def bearer(token_pair: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}
