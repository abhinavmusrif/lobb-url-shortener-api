from collections.abc import Callable
from datetime import datetime, timezone

from app.repository import CreateResult, UrlRecord


class InMemoryUrlRepository:
    def __init__(self) -> None:
        self._by_code: dict[str, UrlRecord] = {}
        self._by_hash: dict[str, UrlRecord] = {}

    async def create_or_get(
        self,
        *,
        original_url: str,
        url_hash: str,
        code_factory: Callable[[], str],
        max_attempts: int = 8,
    ) -> CreateResult:
        existing = self._by_hash.get(url_hash)
        if existing is not None:
            return CreateResult(record=existing, created=False)

        for _ in range(max_attempts):
            code = code_factory()
            if code in self._by_code:
                continue
            record = UrlRecord(
                original_url=original_url,
                short_code=code,
                created_at=datetime.now(timezone.utc),
                click_count=0,
            )
            self._by_code[code] = record
            self._by_hash[url_hash] = record
            return CreateResult(record=record, created=True)

        raise RuntimeError("Test repository could not allocate a code")

    async def resolve_and_increment(self, short_code: str) -> UrlRecord | None:
        record = self._by_code.get(short_code)
        if record is None:
            return None
        updated = UrlRecord(
            original_url=record.original_url,
            short_code=record.short_code,
            created_at=record.created_at,
            click_count=record.click_count + 1,
        )
        self._by_code[short_code] = updated
        return updated

    async def ping(self) -> bool:
        return True
