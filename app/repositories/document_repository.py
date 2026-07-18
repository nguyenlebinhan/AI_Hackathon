from __future__ import annotations

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import UserRole
from app.model.documents import Document
from app.model.security import DocumentGrantPermission, DocumentPermission
from app.model.users import User


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_by_id_and_commune(
        self,
        *,
        document_id: str,
        commune_id: str,
        for_update: bool = False,
    ) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id,
            Document.commune_id == commune_id,
            Document.is_deleted.is_(False),
            Document.deleted_at.is_(None),
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_deleted_by_id_and_commune(
        self,
        *,
        document_id: str,
        commune_id: str,
        for_update: bool = False,
    ) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id,
            Document.commune_id == commune_id,
            Document.is_deleted.is_(True),
            Document.deleted_at.is_not(None),
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def user_has_read_access(
        self,
        *,
        document_id: str,
        commune_id: str,
        user_id: str,
    ) -> bool:
        statement = select(
            exists().where(
                DocumentPermission.document_id == document_id,
                DocumentPermission.commune_id == commune_id,
                DocumentPermission.user_id == user_id,
                DocumentPermission.permission.in_(
                    [DocumentGrantPermission.READ, DocumentGrantPermission.ASK]
                ),
            )
        )
        return bool((await self.session.execute(statement)).scalar_one())

    async def list_visible(
        self,
        *,
        actor: User,
        offset: int,
        limit: int,
    ) -> list[Document]:
        statement = select(Document).where(
            Document.commune_id == actor.commune_id,
            Document.is_deleted.is_(False),
            Document.deleted_at.is_(None),
        )
        if actor.role == UserRole.USER:
            grant_exists = exists().where(
                DocumentPermission.document_id == Document.id,
                DocumentPermission.commune_id == actor.commune_id,
                DocumentPermission.user_id == actor.id,
                DocumentPermission.permission.in_(
                    [DocumentGrantPermission.READ, DocumentGrantPermission.ASK]
                ),
            )
            statement = statement.where(or_(Document.owner_id == actor.id, grant_exists))
        statement = statement.order_by(Document.created_at.desc()).offset(offset).limit(limit)
        return list((await self.session.execute(statement)).scalars())

