from pydantic import Field, model_validator

from app.model.schemas.base import APIModel


class BoundingBox(APIModel):
    x0: float
    y0: float
    x1: float
    y1: float


class CitationAnchor(APIModel):
    citation_id: str
    document_id: str
    page_number: int = Field(ge=1)
    block_id: str | None = None
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    quote: str
    bounding_boxes: list[BoundingBox] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_offsets(self) -> "CitationAnchor":
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset must be greater than or equal to start_offset")
        return self
