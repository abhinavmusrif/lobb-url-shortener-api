# URL Shortener API

A clean, asynchronous URL shortener built for the LOBB Python Development assessment using **FastAPI**, **PostgreSQL**, **asyncpg**, and **raw SQL**.

## Required API

### `POST /shorten`

Accepts an HTTP or HTTPS URL and returns a shortened URL.

```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/a/long/path"}'
```

Example response (`201 Created`):

```json
{
  "original_url": "https://example.com/a/long/path",
  "short_code": "aB3xY9Q",
  "short_url": "http://localhost:8000/aB3xY9Q",
  "created_at": "2026-07-30T13:00:00Z"
}
```

Submitting the same URL again returns the existing mapping with `200 OK`. This avoids duplicate records and gives the endpoint idempotent behavior for identical URLs.

### `GET /{short_code}`

Returns a `307 Temporary Redirect` to the original URL.

```bash
curl -i http://localhost:8000/aB3xY9Q
```

Unknown codes return `404 Not Found`.

### `GET /health`

Checks the API and PostgreSQL connection.

## Run with Docker (recommended)

Requirements: Docker and Docker Compose.

```bash
docker compose up --build
```

Then open:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Stop and remove containers:

```bash
docker compose down
```

To also delete the local database volume:

```bash
docker compose down -v
```

## Run locally

Requirements: Python 3.12+ and PostgreSQL 16+.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Update `DATABASE_URL` in `.env` if your PostgreSQL credentials differ. The application creates the required table and indexes safely at startup using `sql/init.sql`.

## Test and lint

Unit tests do not need PostgreSQL:

```bash
pytest tests/test_api.py
ruff check .
```

Run all tests, including the PostgreSQL integration test:

```bash
# PowerShell
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/url_shortener_test"
pytest

# macOS/Linux
TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/url_shortener_test" pytest
```

GitHub Actions runs linting, unit tests, and the PostgreSQL integration test on every push and pull request.

## Project structure

```text
app/
  config.py       Environment configuration
  database.py     asyncpg pool and schema initialization
  main.py         FastAPI application and routes
  repository.py   Raw SQL persistence layer
  schemas.py      Validated request/response models
  service.py      URL hashing and short-code business logic
sql/
  init.sql         PostgreSQL table, constraints, and indexes
tests/
  test_api.py      Fast API tests using an in-memory repository
  test_postgres_integration.py
Dockerfile
docker-compose.yml
PROJECT_DOCUMENTATION.md
```

## Design decisions

- **Async PostgreSQL access:** `asyncpg` provides non-blocking database I/O and demonstrates raw SQL proficiency.
- **Collision-resistant codes:** seven-character Base62 codes provide approximately 3.5 trillion combinations. A cryptographically secure generator is used, and database uniqueness is the final authority.
- **Safe concurrent inserts:** `ON CONFLICT DO NOTHING` plus bounded retries handles code collisions and concurrent requests for the same URL.
- **Duplicate URL prevention:** a SHA-256 digest is uniquely indexed, avoiding a potentially large index on the complete URL text.
- **Atomic redirect analytics:** URL resolution and click-count increment happen in one SQL statement.
- **Correct redirect semantics:** `307 Temporary Redirect` preserves the incoming HTTP method semantics and avoids claiming that a short URL is permanently immutable.
- **Input validation:** only HTTP/HTTPS URLs are accepted; length is capped and embedded credentials are rejected.
- **Separation of concerns:** API, business logic, configuration, and persistence are isolated for easier testing and maintenance.

## Error behavior

| Situation | Status |
|---|---:|
| New valid URL | `201` |
| Existing valid URL | `200` |
| Invalid URL | `422` |
| Unknown short code | `404` |
| Database unavailable | `503` |
| Exhausted code-generation retries | `503` |

## Production follow-ups

Given more time, I would add Alembic migrations, rate limiting, custom-domain support, abuse protection, distributed caching for popular redirects, metrics/tracing, retention policies, and authenticated analytics endpoints. These were intentionally left out to keep the assessment focused and runnable within the requested timebox.
