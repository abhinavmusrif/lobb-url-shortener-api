"""FastAPI application factory, dependency wiring, and HTTP routes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response, status
from fastapi.responses import RedirectResponse

from app.config import Settings, get_settings
from app.database import Database
from app.repository import (
    PostgresUrlRepository,
    ShortCodeGenerationError,
    UrlRepository,
)
from app.schemas import HealthResponse, ShortenRequest, ShortenResponse
from app.service import UrlShortenerService


@asynccontextmanager
async def database_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the PostgreSQL pool at startup and close it during shutdown."""
    settings: Settings = app.state.settings
    database = Database(settings)
    await database.connect()
    await database.initialize_schema()

    if database.pool is None:
        raise RuntimeError("Database pool was not initialized")

    app.state.database = database
    app.state.repository = PostgresUrlRepository(database.pool)
    try:
        yield
    finally:
        await database.disconnect()


def get_repository(request: Request) -> UrlRepository:
    """Return the repository attached to the current application instance."""
    return request.app.state.repository


def get_service(
    request: Request,
    repository: Annotated[UrlRepository, Depends(get_repository)],
) -> UrlShortenerService:
    """Build the request-scoped service from application dependencies."""
    return UrlShortenerService(repository, request.app.state.settings)


def create_app(
    *,
    settings: Settings | None = None,
    repository: UrlRepository | None = None,
) -> FastAPI:
    """Create the API, optionally injecting dependencies for isolated tests."""
    resolved_settings = settings or get_settings()

    # Injected repositories let unit tests exercise the HTTP layer without
    # opening a real PostgreSQL connection.
    lifespan = None if repository is not None else database_lifespan

    application = FastAPI(
        title=resolved_settings.app_name,
        version="1.0.0",
        description=(
            "A small, production-minded URL shortener built with FastAPI, "
            "PostgreSQL, asyncpg, and raw SQL."
        ),
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    if repository is not None:
        application.state.repository = repository

    @application.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
        summary="Check service and database health",
    )
    async def health(
        repo: Annotated[UrlRepository, Depends(get_repository)],
    ) -> HealthResponse:
        """Confirm that both the API process and database are responsive."""
        if not await repo.ping():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is unavailable",
            )
        return HealthResponse(status="ok")

    @application.post(
        "/shorten",
        response_model=ShortenResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["urls"],
        summary="Create or retrieve a shortened URL",
        responses={
            200: {"description": "The URL had already been shortened"},
            201: {"description": "A new short URL was created"},
            422: {"description": "The supplied URL is invalid"},
            503: {"description": "A unique short code could not be generated"},
        },
    )
    async def shorten_url(
        payload: ShortenRequest,
        response: Response,
        service: Annotated[UrlShortenerService, Depends(get_service)],
    ) -> ShortenResponse:
        """Create a short URL or return the existing idempotent mapping."""
        try:
            result = await service.shorten(str(payload.url))
        except ShortCodeGenerationError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not allocate a short code. Please retry.",
            ) from exc

        # A repeated long URL is a successful lookup rather than a new resource.
        if not result.created:
            response.status_code = status.HTTP_200_OK

        return ShortenResponse(
            original_url=result.record.original_url,
            short_code=result.record.short_code,
            short_url=result.short_url,
            created_at=result.record.created_at,
        )

    @application.get(
        "/{short_code}",
        include_in_schema=True,
        tags=["urls"],
        summary="Redirect to the original URL",
        responses={
            307: {"description": "Redirect to the original URL"},
            404: {"description": "Short code was not found"},
        },
    )
    async def redirect_to_original(
        short_code: Annotated[
            str,
            Path(
                min_length=5,
                max_length=12,
                pattern=r"^[A-Za-z0-9]+$",
                description="Case-sensitive Base62 short code",
            ),
        ],
        service: Annotated[UrlShortenerService, Depends(get_service)],
    ) -> RedirectResponse:
        """Resolve a short code, count the visit, and redirect the client."""
        record = await service.resolve(short_code)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Short URL not found",
            )

        # A 307 redirect avoids claiming the mapping is permanently immutable.
        return RedirectResponse(
            url=record.original_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    return application


app = create_app()
