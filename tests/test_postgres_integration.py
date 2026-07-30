import os
import uuid

import pytest

LifespanManager = pytest.importorskip("asgi_lifespan").LifespanManager
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="Set TEST_DATABASE_URL to run PostgreSQL integration tests",
)


@pytest.mark.asyncio
async def test_api_against_postgres() -> None:
    target = f"https://example.com/integration/{uuid.uuid4()}"
    app = create_app(
        settings=Settings(
            database_url=os.environ["TEST_DATABASE_URL"],
            public_base_url="http://test",
        )
    )

    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            created = await client.post("/shorten", json={"url": target})
            redirected = await client.get(f"/{created.json()['short_code']}")

    assert created.status_code == 201
    assert redirected.status_code == 307
    assert redirected.headers["location"] == target
