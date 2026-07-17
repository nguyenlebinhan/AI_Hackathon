from app.model.schemas.base import APIModel


class SummaryResponse(APIModel):
    document_id: str
    content: str
    citation_ids: list[str]
