from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    cors_origins: str = "http://localhost:5173"

    database_url: str
    celery_broker_url: str
    celery_result_backend: str

    qdrant_url: str
    qdrant_collection_name: str = "image_embeddings"

    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket_name: str
    minio_use_ssl: bool = False

    jwt_secret: str
    jwt_lifetime_seconds: int = 900
    refresh_token_secret: str
    refresh_token_lifetime_seconds: int = 604800

    upload_max_size_mb: int = 25
    upload_allowed_mime_types: str = "image/jpeg,image/png,image/webp"

    clip_model_name: str = "ViT-B-32"
    clip_pretrained: str = "laion2b_s34b_b79k"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def upload_allowed_mime_types_list(self) -> list[str]:
        return [mime.strip() for mime in self.upload_allowed_mime_types.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
