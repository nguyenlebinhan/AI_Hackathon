import re

from pydantic import Field, SecretStr, field_validator

from app.core.permissions import UserRole
from app.schemas.base import StrictAPIModel

_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{3,64}$")
_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class AdminUserCreateRequest(StrictAPIModel):
    # commune_id, created_by and role intentionally do not exist in this body.
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(min_length=5, max_length=320)
    full_name: str = Field(min_length=1, max_length=255)
    position: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    temporary_password: SecretStr = Field(min_length=12, max_length=1024)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not _USERNAME_PATTERN.fullmatch(value):
            raise ValueError("username chỉ được chứa chữ, số, dấu chấm, gạch dưới hoặc gạch ngang")
        return value.casefold()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.casefold()
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("email không hợp lệ")
        return normalized


class AdminResetPasswordRequest(StrictAPIModel):
    temporary_password: SecretStr = Field(min_length=12, max_length=1024)


class UserPublic(StrictAPIModel):
    id: str
    commune_id: str
    username: str
    email: str
    full_name: str
    position: str | None
    department: str | None
    role: UserRole
    is_active: bool
    must_change_password: bool


class StaffDirectoryEntry(StrictAPIModel):
    full_name: str
    position: str | None
    department: str | None
    commune_name: str
