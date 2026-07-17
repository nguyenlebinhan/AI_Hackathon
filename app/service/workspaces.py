from sqlalchemy.orm import Session

from app.model.repositories.workspaces import WorkspaceRepository
from app.model.schemas.workspaces import WorkspaceCreate
from app.model.workspaces import Workspace
from app.service.base import Service


class WorkspaceService(Service):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.repository = WorkspaceRepository(session)

    def create(self, payload: WorkspaceCreate, *, owner_id: str | None = None) -> Workspace:
        workspace = Workspace(
            name=payload.name,
            description=payload.description,
            owner_id=owner_id,
        )
        self.repository.add(workspace)
        self.session.commit()
        self.session.refresh(workspace)
        return workspace
