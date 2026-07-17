from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.repositories.base import Repository
from app.model.users import User, UserStatus


class UserRepository(Repository[User]):
    model = User

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_active(self, user_id: str) -> User | None:
        statement = select(User).where(
            User.id == user_id,
            User.status == UserStatus.ACTIVE,
        )
        return self.session.scalar(statement)
