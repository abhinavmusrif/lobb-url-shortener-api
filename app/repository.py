from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class UrlRecord:
    original_url: str
    short_code: str
    created_at: datetime
    click_count: int


@dataclass(frozen=True, slots=True)
class CreateResult:
    record: UrlRecord
    created: bool


class UrlRepository(Protocol):
    async def create_or_get(
        self,
        *,
        original_url: str,
        url_hash: str,
        code_factory: Callable[[], str],
        max_attempts: int = 8,
    ) -> CreateResult: ...

    async def resolve_and_increment(self, short_code: str) -> UrlRecord | None: ...

    async def ping(self) -> bool: ...


class ShortCodeGenerationError(RuntimeError):
    """Raised when repeated code collisions prevent URL creation."""


class PostgresUrlRepository:
    def __init__(self, pool: Any) -> None:
        self._pool = pool

    @staticmethod
    def _to_record(row: Any) -> UrlRecord:
        return UrlRecord(
            original_url=row["original_url"],
            short_code=row["short_code"],
            created_at=row["created_at"],
            click_count=row["click_count"],
        )

    async def create_or_get(
        self,
        *,
        original_url: str,
        url_hash: str,
        code_factory: Callable[[], str],
        max_attempts: int = 8,
    ) -> CreateResult:
        existing = await self._pool.fetchrow(
            """
            SELECT original_url, short_code, created_at, click_count
            FROM shortened_urls
            WHERE url_hash = $1
            """,
            url_hash,
        )
        if existing is not None:
            return CreateResult(record=self._to_record(existing), created=False)

        for _ in range(max_attempts):
            short_code = code_factory()
            inserted = await self._pool.fetchrow(
                """
                INSERT INTO shortened_urls (short_code, original_url, url_hash)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
                RETURNING original_url, short_code, created_at, click_count
                """,
                short_code,
                original_url,
                url_hash,
            )
            if inserted is not None:
                return CreateResult(record=self._to_record(inserted), created=True)

            # A concurrent request may have inserted the same long URL.
            existing = await self._pool.fetchrow(
                """
                SELECT original_url, short_code, created_at, click_count
                FROM shortened_urls
                WHERE url_hash = $1
                """,
                url_hash,
            )
            if existing is not None:
                return CreateResult(record=self._to_record(existing), created=False)

            # Otherwise the generated short code collided. Generate another code.

        raise ShortCodeGenerationError("Unable to generate a unique short code")

    async def resolve_and_increment(self, short_code: str) -> UrlRecord | None:
        row = await self._pool.fetchrow(
            """
            UPDATE shortened_urls
            SET click_count = click_count + 1
            WHERE short_code = $1
            RETURNING original_url, short_code, created_at, click_count
            """,
            short_code,
        )
        return None if row is None else self._to_record(row)

    async def ping(self) -> bool:
        return await self._pool.fetchval("SELECT TRUE") is True
