import hashlib
import secrets
import string
from dataclasses import dataclass

from app.config import Settings
from app.repository import CreateResult, UrlRecord, UrlRepository

BASE62_ALPHABET = string.ascii_letters + string.digits


@dataclass(frozen=True, slots=True)
class ShortenResult:
    record: UrlRecord
    short_url: str
    created: bool


class UrlShortenerService:
    def __init__(self, repository: UrlRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    def _generate_code(self) -> str:
        return "".join(
            secrets.choice(BASE62_ALPHABET)
            for _ in range(self._settings.short_code_length)
        )

    async def shorten(self, original_url: str) -> ShortenResult:
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
        return await self._repository.resolve_and_increment(short_code)
