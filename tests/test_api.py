import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app
from tests.fakes import InMemoryUrlRepository


@pytest.fixture
def app():
    return create_app(
        settings=Settings(public_base_url="https://sho.rt"),
        repository=InMemoryUrlRepository(),
    )


@pytest.mark.asyncio
async def test_shorten_create_and_reuse(app) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        first = await client.post(
            "/shorten",
            json={"url": "https://example.com/articles/fastapi"},
        )
        second = await client.post(
            "/shorten",
            json={"url": "https://example.com/articles/fastapi"},
        )

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["short_code"] == second.json()["short_code"]
    assert first.json()["short_url"].startswith("https://sho.rt/")


@pytest.mark.asyncio
async def test_redirect_and_missing_code(app) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        created = await client.post(
            "/shorten",
            json={"url": "https://example.com/target"},
        )
        short_code = created.json()["short_code"]

        redirect = await client.get(f"/{short_code}")
        missing = await client.get("/Missing1")

    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://example.com/target"
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_invalid_url_is_rejected(app) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/shorten",
            json={"url": "not-a-valid-url"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_health(app) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
