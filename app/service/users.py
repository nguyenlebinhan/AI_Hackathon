from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.model.repositories.users import UserRepository
from app.model.users import User
from app.service.base import Service


class UserService(Service):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.repository = UserRepository(session)

    def get_active(self, user_id: str) -> User:
        user = self.repository.get_active(user_id)
        if user is None:
            raise NotFoundError("USER", user_id)
        return user
