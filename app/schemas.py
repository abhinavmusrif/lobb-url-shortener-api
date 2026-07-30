"""Pydantic request and response models for the public API."""

from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class ShortenRequest(BaseModel):
    """Validated payload accepted by POST /shorten."""

    url: AnyHttpUrl = Field(description="The HTTP or HTTPS URL to shorten")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        """Reject impractically long URLs and embedded user credentials."""
        rendered = str(value)
        if len(rendered) > 2048:
            raise ValueError("URL must not exceed 2048 characters")
        if value.username is not None or value.password is not None:
            raise ValueError("URLs containing embedded credentials are not allowed")
        return value


class ShortenResponse(BaseModel):
    """Public representation of a stored short-URL mapping."""

    model_config = ConfigDict(from_attributes=True)

    original_url: str
    short_code: str
    short_url: str
    created_at: datetime


class HealthResponse(BaseModel):
    """Response returned when the API and database are healthy."""

    status: str
