from datetime import datetime
from typing import Literal

from pydantic import Field, SecretStr

from app.core.permissions import UserRole
from app.schemas.base import StrictAPIModel


class LoginRequest(StrictAPIModel):
    identifier: str = Field(min_length=3, max_length=320)
    password: SecretStr = Field(min_length=1, max_length=1024)
    device_name: str | None = Field(default=None, max_length=255)


class RefreshRequest(StrictAPIModel):
    refresh_token: SecretStr = Field(min_length=1, max_length=512)


class ChangePasswordRequest(StrictAPIModel):
    current_password: SecretStr = Field(min_length=1, max_length=1024)
    new_password: SecretStr = Field(min_length=12, max_length=1024)


class TokenPairResponse(StrictAPIModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    refresh_expires_at: datetime
    must_change_password: bool


class AccessTokenClaims(StrictAPIModel):
    sub: str = Field(min_length=1, max_length=40)
    role: UserRole
    commune_id: str = Field(min_length=36, max_length=36)
    session_id: str = Field(min_length=36, max_length=36)
    token_version: int = Field(ge=1)
    type: Literal["access"]
    iat: int
    nbf: int
    exp: int
    jti: str
    iss: str
    aud: str
