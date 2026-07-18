from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import Settings
from app.core.security import create_access_token, parse_refresh_token
from app.model.security import AuthSession
from app.tests.security.conftest import (
    TEST_PASSWORD,
    bearer,
    login_as,
)


@pytest.mark.anyio
async def test_login_success_wrong_password_and_safe_me_response(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    tokens = await login_as(async_client, "admin.a")
    assert tokens["expires_in"] == 600
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    me = await async_client.get("/api/v1/auth/me", headers=bearer(tokens))
    assert me.status_code == 200
    body = me.json()
    assert body["commune_id"] == security_data["commune_a"].id
    assert body["role"] == "ADMIN"
    serialized = me.text.casefold()
    assert "password_hash" not in serialized
    assert "refresh_token" not in serialized

    denied = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin.a", "password": "Wrong-Password-Value-99!"},
    )
    assert denied.status_code == 401
    assert denied.headers["www-authenticate"] == "Bearer"

    reflected_secret = "short-secret-value"
    validation_error = await async_client.post(
        "/api/v1/auth/change-password",
        headers=bearer(tokens),
        json={
            "current_password": TEST_PASSWORD,
            "new_password": reflected_secret,
            "unexpected": "field",
        },
    )
    assert validation_error.status_code == 422
    assert reflected_secret not in validation_error.text


@pytest.mark.anyio
async def test_failed_login_limit_returns_429(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    del security_data
    for _ in range(4):
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"identifier": "user.a", "password": "Wrong-Password-Value-99!"},
        )
        assert response.status_code == 401
    limited = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "user.a", "password": "Wrong-Password-Value-99!"},
    )
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0

    still_limited = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "user.a", "password": TEST_PASSWORD},
    )
    assert still_limited.status_code == 429


@pytest.mark.anyio
async def test_expired_access_token_is_rejected(
    async_client: AsyncClient,
    security_data: dict[str, Any],
    security_settings: Settings,
) -> None:
    tokens = await login_as(async_client, "user.a")
    claims = jwt.decode(
        tokens["access_token"],
        options={"verify_signature": False},
        algorithms=["HS256"],
    )
    user = security_data["user_a"]
    expired = create_access_token(
        user_id=user.id,
        role=user.role,
        commune_id=user.commune_id,
        session_id=claims["session_id"],
        token_version=user.token_version,
        settings=security_settings,
        now=datetime.now(UTC) - timedelta(minutes=2),
        expires_delta=timedelta(minutes=1),
    )
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_expired_refresh_token_is_rejected(
    async_client: AsyncClient,
    security_data: dict[str, Any],
    security_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    del security_data
    tokens = await login_as(async_client, "user.a")
    session_id = parse_refresh_token(tokens["refresh_token"])
    async with security_session_factory() as session:
        auth_session = (
            await session.execute(select(AuthSession).where(AuthSession.id == session_id))
        ).scalar_one()
        auth_session.created_at = datetime.now(UTC) - timedelta(seconds=2)
        auth_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_rotation_and_old_token_reuse_revokes_family(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    del security_data
    first = await login_as(async_client, "user.a")
    rotated_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert rotated_response.status_code == 200
    rotated = rotated_response.json()
    assert rotated["refresh_token"] != first["refresh_token"]

    reuse = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "REFRESH_TOKEN_REUSE_DETECTED"

    family_revoked = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotated["refresh_token"]},
    )
    assert family_revoked.status_code == 401


@pytest.mark.anyio
async def test_logout_revokes_one_device(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    del security_data
    tokens = await login_as(async_client, "user.a")
    other_device = await login_as(async_client, "user.a")
    logout = await async_client.post(
        "/api/v1/auth/logout",
        headers=bearer(tokens),
    )
    assert logout.status_code == 204
    assert (await async_client.get("/api/v1/auth/me", headers=bearer(tokens))).status_code == 401
    refresh = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 401
    assert (
        await async_client.get("/api/v1/auth/me", headers=bearer(other_device))
    ).status_code == 200


@pytest.mark.anyio
async def test_logout_all_revokes_every_device(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    del security_data
    device_one = await login_as(async_client, "user.a")
    device_two = await login_as(async_client, "user.a")
    response = await async_client.post(
        "/api/v1/auth/logout-all",
        headers=bearer(device_one),
    )
    assert response.status_code == 204
    assert (
        await async_client.get("/api/v1/auth/me", headers=bearer(device_two))
    ).status_code == 401
    assert (
        await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": device_two["refresh_token"]},
        )
    ).status_code == 401


@pytest.mark.anyio
async def test_change_password_invalidates_old_sessions(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    del security_data
    old_tokens = await login_as(async_client, "user.a")
    new_password = "New-Secure-Password-2026!"
    changed = await async_client.post(
        "/api/v1/auth/change-password",
        headers=bearer(old_tokens),
        json={
            "current_password": TEST_PASSWORD,
            "new_password": new_password,
        },
    )
    assert changed.status_code == 204
    assert (
        await async_client.get("/api/v1/auth/me", headers=bearer(old_tokens))
    ).status_code == 401
    assert (
        await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_tokens["refresh_token"]},
        )
    ).status_code == 401

    old_login = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "user.a", "password": TEST_PASSWORD},
    )
    assert old_login.status_code == 401
    new_login = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "user.a", "password": new_password},
    )
    assert new_login.status_code == 200


@pytest.mark.anyio
async def test_admin_reset_password_revokes_sessions_and_requires_change(
    async_client: AsyncClient,
    security_data: dict[str, Any],
) -> None:
    user_tokens = await login_as(async_client, "user.a")
    admin_tokens = await login_as(async_client, "admin.a")
    temporary_password = "Temporary-Reset-Password-77!"
    reset = await async_client.post(
        f"/api/v1/admin/users/{security_data['user_a'].id}/reset-password",
        headers=bearer(admin_tokens),
        json={"temporary_password": temporary_password},
    )
    assert reset.status_code == 204
    assert (
        await async_client.get("/api/v1/auth/me", headers=bearer(user_tokens))
    ).status_code == 401
    assert (
        await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": user_tokens["refresh_token"]},
        )
    ).status_code == 401

    temporary_login = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "user.a", "password": temporary_password},
    )
    assert temporary_login.status_code == 200
    temporary_tokens = temporary_login.json()
    assert temporary_tokens["must_change_password"] is True
    gated = await async_client.get(
        "/api/v1/documents",
        headers=bearer(temporary_tokens),
    )
    assert gated.status_code == 403
    assert gated.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    permanent_password = "Permanent-Password-After-Reset-88!"
    changed = await async_client.post(
        "/api/v1/auth/change-password",
        headers=bearer(temporary_tokens),
        json={
            "current_password": temporary_password,
            "new_password": permanent_password,
        },
    )
    assert changed.status_code == 204
    assert (
        await async_client.post(
            "/api/v1/auth/login",
            json={"identifier": "user.a", "password": permanent_password},
        )
    ).status_code == 200
