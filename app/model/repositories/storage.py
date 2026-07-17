from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.repositories.base import Repository
from app.model.storage import DocumentFile


class DocumentFileRepository(Repository[DocumentFile]):
    model = DocumentFile

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def list_for_document(
        self,
        document_id: str,
        *,
        include_deleted: bool = False,
    ) -> list[DocumentFile]:
        statement = select(DocumentFile).where(DocumentFile.document_id == document_id)
        if not include_deleted:
            statement = statement.where(DocumentFile.deleted_at.is_(None))
        return list(self.session.scalars(statement))
