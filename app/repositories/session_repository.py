from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.security import (
    AuthSession,
    RefreshTokenHistory,
    RefreshTokenHistoryStatus,
)


class AuthSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, auth_session: AuthSession) -> AuthSession:
        self.session.add(auth_session)
        return auth_session

    async def get_by_id_for_refresh(
        self,
        session_id: str,
        *,
        for_update: bool = True,
    ) -> AuthSession | None:
        statement = select(AuthSession).where(AuthSession.id == session_id)
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_by_id_and_user(
        self,
        *,
        session_id: str,
        user_id: str,
    ) -> AuthSession | None:
        statement = select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def find_history(
        self,
        *,
        session_id: str,
        token_hash: str,
    ) -> RefreshTokenHistory | None:
        statement = select(RefreshTokenHistory).where(
            RefreshTokenHistory.session_id == session_id,
            RefreshTokenHistory.token_hash == token_hash,
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    def add_rotated_history(
        self,
        *,
        session_id: str,
        token_hash: str,
        used_at: datetime,
    ) -> RefreshTokenHistory:
        history = RefreshTokenHistory(
            session_id=session_id,
            token_hash=token_hash,
            status=RefreshTokenHistoryStatus.ROTATED,
            used_at=used_at,
        )
        self.session.add(history)
        return history

    async def revoke_user_sessions(
        self,
        *,
        user_id: str,
        revoked_at: datetime,
        reason: str,
    ) -> None:
        await self.session.execute(
            update(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at, revoke_reason=reason)
        )

    async def revoke_family(
        self,
        *,
        token_family_id: str,
        revoked_at: datetime,
        reason: str,
    ) -> None:
        await self.session.execute(
            update(AuthSession)
            .where(
                AuthSession.token_family_id == token_family_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at, revoke_reason=reason)
        )

