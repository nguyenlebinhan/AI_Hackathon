from datetime import datetime

from pydantic import Field, field_validator

from app.model.schemas.base import APIModel
from app.model.workspaces import WorkspaceStatus


class WorkspaceCreate(APIModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Tên workspace không được để trống")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class WorkspaceResponse(APIModel):
    id: str
    name: str
    description: str | None
    status: WorkspaceStatus
    created_at: datetime
