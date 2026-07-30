"""Business logic for generating, storing, and resolving short URLs."""

import hashlib
import secrets
import string
from dataclasses import dataclass

from app.config import Settings
from app.repository import CreateResult, UrlRecord, UrlRepository

BASE62_ALPHABET = string.ascii_letters + string.digits


@dataclass(frozen=True, slots=True)
class ShortenResult:
    """Service response containing the stored mapping and public short URL."""

    record: UrlRecord
    short_url: str
    created: bool


class UrlShortenerService:
    """Coordinate short-code generation independently of the HTTP layer."""

    def __init__(self, repository: UrlRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    def _generate_code(self) -> str:
        """Generate a cryptographically strong, case-sensitive Base62 code."""
        return "".join(
            secrets.choice(BASE62_ALPHABET)
            for _ in range(self._settings.short_code_length)
        )

    async def shorten(self, original_url: str) -> ShortenResult:
        """Create or retrieve the stable short mapping for a validated URL."""
        # The digest is a fixed-size database key for deduplication. It is not
        # used as a password hash or exposed to clients.
        url_hash = hashlib.sha256(original_url.encode("utf-8")).hexdigest()
        result: CreateResult = await self._repository.create_or_get(
            original_url=original_url,
            url_hash=url_hash,
            code_factory=self._generate_code,
        )
        return ShortenResult(
            record=result.record,
            short_url=(
                f"{self._settings.normalized_public_base_url}/"
                f"{result.record.short_code}"
            ),
            created=result.created,
        )

    async def resolve(self, short_code: str) -> UrlRecord | None:
        """Resolve a short code while recording the redirect visit."""
        return await self._repository.resolve_and_increment(short_code)
