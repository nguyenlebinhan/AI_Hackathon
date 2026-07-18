from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.model.documents import Document
from app.model.security import DocumentGrantPermission, DocumentPermission
from app.model.users import User
from app.tests.security.conftest import bearer, login_as


@pytest.mark.anyio
async def test_admin_user_management_is_commune_scoped(
    async_client: AsyncClient,
    security_data: dict[str, Any],
    security_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    admin_a = await login_as(async_client, "admin.a")
    listed = await async_client.get(
        "/api/v1/admin/users",
        headers=bearer(admin_a),
    )
    assert listed.status_code == 200
    assert {item["commune_id"] for item in listed.json()} == {security_data["commune_a"].id}

    cross_tenant_lock = await async_client.patch(
        f"/api/v1/admin/users/{security_data['user_b'].id}/lock",
        headers=bearer(admin_a),
    )
    assert cross_tenant_lock.status_code == 404
    async with security_session_factory() as session:
        user_b = (
            await session.execute(select(User).where(User.id == security_data["user_b"].id))
        ).scalar_one()
        assert user_b.is_active is True


@pytest.mark.anyio
async def test_user_cannot_call_admin_api(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    del security_data
    user = await login_as(async_client, "user.a")
    response = await async_client.get(
        "/api/v1/admin/users",
        headers=bearer(user),
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_lock_revokes_existing_access_token(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    user_tokens = await login_as(async_client, "user.a")
    admin_tokens = await login_as(async_client, "admin.a")
    locked = await async_client.patch(
        f"/api/v1/admin/users/{security_data['user_a'].id}/lock",
        headers=bearer(admin_tokens),
    )
    assert locked.status_code == 200
    assert locked.json()["is_active"] is False
    assert (
        await async_client.get("/api/v1/auth/me", headers=bearer(user_tokens))
    ).status_code == 401
    unlocked = await async_client.patch(
        f"/api/v1/admin/users/{security_data['user_a'].id}/unlock",
        headers=bearer(admin_tokens),
    )
    assert unlocked.status_code == 200
    assert unlocked.json()["is_active"] is True
    # Unlocking does not resurrect sessions revoked by the lock.
    assert (
        await async_client.get("/api/v1/auth/me", headers=bearer(user_tokens))
    ).status_code == 401
    assert (await login_as(async_client, "user.a"))["access_token"]


@pytest.mark.anyio
async def test_document_read_blocks_idor_and_allows_explicit_share(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    user_a = await login_as(async_client, "user.a")
    shared = await async_client.get(
        f"/api/v1/documents/{security_data['doc_shared'].id}",
        headers=bearer(user_a),
    )
    assert shared.status_code == 200
    cross_tenant = await async_client.get(
        f"/api/v1/documents/{security_data['doc_b'].id}",
        headers=bearer(user_a),
    )
    assert cross_tenant.status_code == 404

    visible = await async_client.get(
        "/api/v1/documents",
        headers=bearer(user_a),
    )
    visible_ids = {item["id"] for item in visible.json()}
    assert security_data["doc_shared"].id in visible_ids
    assert security_data["doc_b"].id not in visible_ids


@pytest.mark.anyio
async def test_user_document_delete_policy_and_soft_delete(
    async_client: AsyncClient,
    security_data: dict[str, Any],
    security_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user_a = await login_as(async_client, "user.a")
    own = await async_client.delete(
        f"/api/v1/documents/{security_data['doc_own'].id}",
        headers=bearer(user_a),
    )
    assert own.status_code == 204
    assert (
        await async_client.get(
            f"/api/v1/documents/{security_data['doc_own'].id}",
            headers=bearer(user_a),
        )
    ).status_code == 404
    async with security_session_factory() as session:
        stored = (
            await session.execute(
                select(Document).where(Document.id == security_data["doc_own"].id)
            )
        ).scalar_one()
        assert stored.is_deleted is True
        assert stored.deleted_at is not None
        assert stored.deleted_by == security_data["user_a"].id

    for key in ("doc_other", "doc_approved", "doc_pending", "doc_meeting"):
        denied = await async_client.delete(
            f"/api/v1/documents/{security_data[key].id}",
            headers=bearer(user_a),
        )
        assert denied.status_code == 403, key


@pytest.mark.anyio
async def test_admin_delete_restore_still_requires_same_commune(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    admin_a = await login_as(async_client, "admin.a")
    admin_b = await login_as(async_client, "admin.b")
    deleted = await async_client.delete(
        f"/api/v1/documents/{security_data['doc_other'].id}",
        headers=bearer(admin_a),
    )
    assert deleted.status_code == 204
    restored = await async_client.post(
        f"/api/v1/documents/{security_data['doc_other'].id}/restore",
        headers=bearer(admin_a),
    )
    assert restored.status_code == 200

    cross_delete = await async_client.delete(
        f"/api/v1/documents/{security_data['doc_own'].id}",
        headers=bearer(admin_b),
    )
    assert cross_delete.status_code == 404

    user_a = await login_as(async_client, "user.a")
    user_restore = await async_client.post(
        f"/api/v1/documents/{security_data['doc_deleted'].id}/restore",
        headers=bearer(user_a),
    )
    assert user_restore.status_code == 403


@pytest.mark.anyio
async def test_audit_logs_are_tenant_scoped_and_have_no_mutation_routes(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    admin_a = await login_as(async_client, "admin.a")
    listed = await async_client.get(
        "/api/v1/admin/audit-logs",
        headers=bearer(admin_a),
    )
    assert listed.status_code == 200
    assert all(item["commune_id"] == security_data["commune_a"].id for item in listed.json())

    cross = await async_client.get(
        f"/api/v1/admin/audit-logs/{security_data['audit_b'].id}",
        headers=bearer(admin_a),
    )
    assert cross.status_code == 404
    own_id = listed.json()[0]["id"]
    assert (
        await async_client.delete(
            f"/api/v1/admin/audit-logs/{own_id}",
            headers=bearer(admin_a),
        )
    ).status_code == 405
    assert (
        await async_client.patch(
            f"/api/v1/admin/audit-logs/{own_id}",
            headers=bearer(admin_a),
            json={"reason": "tamper"},
        )
    ).status_code == 405


@pytest.mark.anyio
async def test_province_directory_is_field_limited_not_admin_scope(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    admin_a = await login_as(async_client, "admin.a")
    directory = await async_client.get(
        "/api/v1/staff-directory",
        headers=bearer(admin_a),
    )
    assert directory.status_code == 200
    entries = directory.json()
    assert {"Xã A", "Xã B"} <= {entry["commune_name"] for entry in entries}
    assert set(entries[0]) == {
        "full_name",
        "position",
        "department",
        "commune_name",
    }
    serialized = directory.text.casefold()
    for forbidden in ("email", "password", "token", "ip_address", "is_active"):
        assert forbidden not in serialized

    still_not_manageable = await async_client.patch(
        f"/api/v1/admin/users/{security_data['user_b'].id}/lock",
        headers=bearer(admin_a),
    )
    assert still_not_manageable.status_code == 404


@pytest.mark.anyio
async def test_server_owned_fields_cannot_be_injected(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    admin_a = await login_as(async_client, "admin.a")
    base_payload = {
        "username": "new.user",
        "email": "new.user@example.gov.vn",
        "full_name": "New User",
        "temporary_password": "Temporary-Password-42!",
    }
    for injected in (
        {"commune_id": security_data["commune_b"].id},
        {"role": "ADMIN"},
        {"created_by": security_data["admin_b"].id},
    ):
        response = await async_client.post(
            "/api/v1/admin/users",
            headers=bearer(admin_a),
            json=base_payload | injected,
        )
        assert response.status_code == 422


@pytest.mark.anyio
async def test_admin_create_user_forces_same_commune_and_user_role(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    admin_a = await login_as(async_client, "admin.a")
    created = await async_client.post(
        "/api/v1/admin/users",
        headers=bearer(admin_a),
        json={
            "username": "new.user",
            "email": "new.user@example.gov.vn",
            "full_name": "New User",
            "position": "Cán bộ",
            "department": "Văn phòng",
            "temporary_password": "Temporary-Password-42!",
        },
    )
    assert created.status_code == 201
    assert created.json()["commune_id"] == security_data["commune_a"].id
    assert created.json()["role"] == "USER"
    assert "password_hash" not in created.text.casefold()


@pytest.mark.anyio
async def test_database_rejects_cross_tenant_document_grant(
    security_data: dict[str, Any],
    security_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with security_session_factory() as session:
        session.add(
            DocumentPermission(
                document_id=security_data["doc_b"].id,
                user_id=security_data["user_a"].id,
                commune_id=security_data["commune_a"].id,
                permission=DocumentGrantPermission.READ,
                granted_by=security_data["admin_a"].id,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
