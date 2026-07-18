from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.documents import Document
from app.model.repositories.base import Repository


class DocumentRepository(Repository[Document]):
    model = Document

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_active(self, document_id: str, *, for_update: bool = False) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
            Document.is_deleted.is_(False),
        )
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def find_active_duplicate(self, workspace_id: str, checksum: str) -> Document | None:
        statement = (
            select(Document)
            .where(
                Document.workspace_id == workspace_id,
                Document.checksum == checksum,
                Document.deleted_at.is_(None),
                Document.is_deleted.is_(False),
            )
            .order_by(Document.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)
