"""Typed application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validate runtime settings from the environment and optional .env file."""

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
        """Return a base URL safe for appending a slash and short code."""
        return self.public_base_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    """Build settings once and reuse them for the process lifetime."""
    return Settings()
