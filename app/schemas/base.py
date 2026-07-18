from pydantic import BaseModel, ConfigDict


class StrictAPIModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )

