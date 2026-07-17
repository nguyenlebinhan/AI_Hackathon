from datetime import datetime

from app.model.schemas.base import APIModel
from app.model.storage import StorageProvider


class DocumentFileMetadata(APIModel):
    id: str
    document_id: str
    storage_provider: StorageProvider
    bucket_name: str
    object_key: str
    mime_type: str
    file_size: int
    checksum: str
    created_at: datetime
