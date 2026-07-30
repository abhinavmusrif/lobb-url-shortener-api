CREATE TABLE IF NOT EXISTS shortened_urls (
    id BIGSERIAL PRIMARY KEY,
    short_code VARCHAR(12) NOT NULL UNIQUE,
    original_url TEXT NOT NULL,
    url_hash CHAR(64) NOT NULL UNIQUE,
    click_count BIGINT NOT NULL DEFAULT 0 CHECK (click_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT short_code_length CHECK (char_length(short_code) BETWEEN 5 AND 12)
);

CREATE INDEX IF NOT EXISTS idx_shortened_urls_created_at
    ON shortened_urls (created_at DESC);
