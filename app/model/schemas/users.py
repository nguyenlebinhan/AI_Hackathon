from datetime import datetime

from app.model.schemas.base import APIModel
from app.model.users import UserStatus


class UserResponse(APIModel):
    id: str
    email: str
    full_name: str
    status: UserStatus
    created_at: datetime
