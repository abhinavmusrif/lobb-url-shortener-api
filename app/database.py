"""PostgreSQL connection-pool and schema lifecycle management."""

from pathlib import Path
from typing import Any

from app.config import Settings


class Database:
    """Own the asyncpg connection pool and schema initialization."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.pool: Any | None = None

    async def connect(self) -> None:
        """Create the shared asyncpg pool used by repository operations."""
        # Import lazily so API unit tests can run without opening PostgreSQL.
        # The production dependency remains declared in requirements.txt.
        import asyncpg

        self.pool = await asyncpg.create_pool(
            dsn=self._settings.database_url,
            min_size=self._settings.database_pool_min_size,
            max_size=self._settings.database_pool_max_size,
            command_timeout=10,
        )

    async def initialize_schema(self) -> None:
        """Apply the idempotent table and index definitions from init.sql."""
        if self.pool is None:
            raise RuntimeError("Database pool has not been initialized")

        schema_path = Path(__file__).resolve().parent.parent / "sql" / "init.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        async with self.pool.acquire() as connection:
            await connection.execute(schema_sql)

    async def disconnect(self) -> None:
        """Close every pooled connection during application shutdown."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
