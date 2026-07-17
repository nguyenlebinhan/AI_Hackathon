import re

from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
    )


class MessageResponse(APIModel):
    message: str


DOCUMENT_ID_PATTERN = re.compile(r"^doc-[0-9a-fA-F-]{36}$")
WORKSPACE_ID_PATTERN = re.compile(r"^ws-[0-9a-fA-F-]{36}$")
