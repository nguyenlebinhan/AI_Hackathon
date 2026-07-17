from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings.

    Environment variables use the ``VADS_`` prefix. Lists such as
    ``VADS_CORS_ORIGINS`` are encoded as JSON arrays.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="VADS_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str
    environment: Literal["local", "test", "staging", "production"]
    debug: bool
    api_prefix: str

    database_url: str
    database_echo: bool

    redis_url: str
    celery_broker_url: str
    celery_result_backend: str
    celery_task_always_eager: bool
    document_processing_queue: str

    storage_provider: Literal["MINIO", "S3"]
    s3_endpoint_url: str | None
    s3_access_key: str
    s3_secret_key: SecretStr
    s3_bucket_name: str
    s3_region: str
    s3_force_path_style: bool

    max_upload_size_mb: int = Field(ge=1, le=1024)
    upload_spool_memory_mb: int = Field(ge=1, le=128)
    delete_object_on_soft_delete: bool

    cors_origins: list[str]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_spool_memory_bytes(self) -> int:
        return self.upload_spool_memory_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
