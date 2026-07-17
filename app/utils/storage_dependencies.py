from functools import lru_cache

from app.config.settings import get_settings
from app.service.storage import ObjectStorage, S3ObjectStorage


@lru_cache
def get_object_storage() -> ObjectStorage:
    return S3ObjectStorage(get_settings())
