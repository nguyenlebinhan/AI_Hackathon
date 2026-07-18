from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import UserRole
from app.model.tenancy import Commune
from app.model.users import User, UserStatus


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_identifier_for_login(
        self,
        identifier: str,
        *,
        for_update: bool = False,
    ) -> User | None:
        normalized = identifier.strip().casefold()
        statement = select(User).where(
            or_(
                func.lower(User.username) == normalized,
                func.lower(User.email) == normalized,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_by_id_for_auth(self, user_id: str) -> User | None:
        # Safe exception to tenant-scoped lookup: the ID comes from a verified
        # JWT and is immediately cross-checked against its commune claim.
        statement = select(User).where(User.id == user_id)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_by_id_and_commune(
        self,
        *,
        user_id: str,
        commune_id: str,
        for_update: bool = False,
    ) -> User | None:
        statement = select(User).where(
            User.id == user_id,
            User.commune_id == commune_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_by_commune(
        self,
        *,
        commune_id: str,
        offset: int,
        limit: int,
    ) -> list[User]:
        statement = (
            select(User)
            .where(User.commune_id == commune_id)
            .order_by(User.full_name, User.id)
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars())

    async def list_directory_by_province(
        self,
        *,
        requester_commune_id: str,
        offset: int,
        limit: int,
    ) -> list[dict[str, str | None]]:
        province_id = (
            await self.session.execute(
                select(Commune.province_id).where(Commune.id == requester_commune_id)
            )
        ).scalar_one()
        statement = (
            select(
                User.full_name,
                User.position,
                User.department,
                Commune.name.label("commune_name"),
            )
            .join(Commune, Commune.id == User.commune_id)
            .where(
                Commune.province_id == province_id,
                User.is_active.is_(True),
                User.status == UserStatus.ACTIVE,
            )
            .order_by(Commune.name, User.full_name)
            .offset(offset)
            .limit(limit)
        )
        return [dict(row) for row in (await self.session.execute(statement)).mappings()]

    async def count_active_admins(self, commune_id: str) -> int:
        statement = select(func.count(User.id)).where(
            User.commune_id == commune_id,
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
            User.status == UserStatus.ACTIVE,
        )
        return int((await self.session.execute(statement)).scalar_one())

    def add(self, user: User) -> User:
        self.session.add(user)
        return user

