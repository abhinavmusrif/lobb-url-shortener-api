# URL Shortener API - Project Documentation

**Candidate:** Abhinav Musrif  
**Assessment:** LOBB Python Development Internship  
**Technology:** FastAPI, PostgreSQL, asyncpg, Docker

## 1. Project summary

This project implements the two requested operations:

1. `POST /shorten` accepts a long HTTP/HTTPS URL and returns a shortened URL.
2. `GET /{short_code}` redirects the client to the original URL.

The implementation uses asynchronous FastAPI handlers and raw PostgreSQL queries through `asyncpg`. It also includes input validation, duplicate prevention, code-collision handling, health checks, automated tests, Docker packaging, and interactive API documentation.

## 2. Architecture

The code is separated into clear layers:

- `main.py`: HTTP routes, status codes, dependency injection, and application lifecycle.
- `service.py`: URL hashing and secure Base62 short-code generation.
- `repository.py`: raw SQL queries and PostgreSQL persistence.
- `database.py`: async connection-pool setup and schema initialization.
- `schemas.py`: Pydantic validation and API response contracts.
- `config.py`: environment-based configuration.

This separation keeps route handlers small and allows the API logic to be tested without requiring a running database.

## 3. Database schema

The `shortened_urls` table stores:

- generated short code (unique),
- original URL,
- SHA-256 URL digest (unique),
- click count,
- creation timestamp.

The URL digest prevents duplicate entries without placing a large unique index directly on the URL text. The short-code unique constraint is the source of truth for collision prevention.

## 4. API behavior

### POST /shorten

Request:

```json
{"url": "https://example.com/a/long/path"}
```

Response for a new URL: `201 Created`.

Response for a URL already stored: `200 OK`, returning the same short code.

### GET /{short_code}

Returns `307 Temporary Redirect` with the original URL in the `Location` header. Missing codes return `404 Not Found`.

### GET /health

Returns `200 OK` only when the repository/database responds successfully.

## 5. Running the project

### Recommended: Docker Compose

```bash
docker compose up --build
```

Open Swagger documentation at `http://localhost:8000/docs`.

### Local Python setup

1. Install Python 3.12+ and PostgreSQL 16+.
2. Create and activate a virtual environment.
3. Run `pip install -r requirements-dev.txt`.
4. Copy `.env.example` to `.env` and adjust `DATABASE_URL` if required.
5. Run `uvicorn app.main:app --reload`.

The schema is created safely at application startup.

## 6. Testing

Run unit tests and linting:

```bash
pytest tests/test_api.py
ruff check .
```

To run the PostgreSQL integration test, set `TEST_DATABASE_URL` and execute `pytest`.

The repository includes GitHub Actions CI with a PostgreSQL service container, so linting, unit tests, and integration tests run automatically.

## 7. Engineering choices

- Async database pool for efficient I/O.
- Raw parameterized SQL to prevent SQL injection and demonstrate SQL proficiency.
- Secure Base62 code generation with bounded collision retries.
- Atomic redirect lookup and click-count increment.
- URL validation restricted to HTTP/HTTPS.
- Non-root Docker container.
- Environment variables for configuration and no committed secrets.
- In-memory repository used only in unit tests for fast, deterministic API testing.

## 8. Possible production enhancements

For a production system, I would add Alembic migrations, request rate limiting, abuse detection, observability, a Redis redirect cache, authenticated analytics, custom aliases/domains, expiration support, and deployment-specific secret management.
