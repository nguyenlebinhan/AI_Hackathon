from pydantic import Field

from app.model.schemas.base import APIModel


class ExtractedBlock(APIModel):
    block_id: str
    document_id: str
    page_number: int = Field(ge=1)
    text: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
