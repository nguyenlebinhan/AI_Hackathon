from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.security import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_commune(
        self,
        *,
        commune_id: str,
        offset: int,
        limit: int,
    ) -> list[AuditLog]:
        statement = (
            select(AuditLog)
            .where(AuditLog.commune_id == commune_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars())

    async def get_by_id_and_commune(
        self,
        *,
        audit_log_id: str,
        commune_id: str,
    ) -> AuditLog | None:
        statement = select(AuditLog).where(
            AuditLog.id == audit_log_id,
            AuditLog.commune_id == commune_id,
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

