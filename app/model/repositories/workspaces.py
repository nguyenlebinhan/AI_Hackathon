from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.repositories.base import Repository
from app.model.workspaces import Workspace, WorkspaceStatus


class WorkspaceRepository(Repository[Workspace]):
    model = Workspace

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_active(self, workspace_id: str, *, for_update: bool = False) -> Workspace | None:
        statement = select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.status == WorkspaceStatus.ACTIVE,
            Workspace.deleted_at.is_(None),
        )
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)
