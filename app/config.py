from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "LOBB URL Shortener API"
    environment: str = "development"
    database_url: str = "postgresql://localhost:5432/url_shortener"
    public_base_url: str = "http://localhost:8000"
    short_code_length: int = Field(default=7, ge=5, le=12)
    database_pool_min_size: int = Field(default=1, ge=1, le=20)
    database_pool_max_size: int = Field(default=10, ge=1, le=50)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def normalized_public_base_url(self) -> str:
        return self.public_base_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
