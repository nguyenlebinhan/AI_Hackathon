from app.model.schemas.base import APIModel


class VectorChunkReference(APIModel):
    chunk_id: str
    document_id: str
    citation_id: str
