"""Typed application settings loaded from the environment or a local .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
EXAMPLE_URL = "postgresql://climate_reader:password@host/dbname?sslmode=require"
_POSTGRES_DRIVERS = {
    "postgres",
    "postgresql",
    "postgresql+psycopg",
    "postgresql+psycopg2",
}


class Settings(BaseSettings):
    """Validated runtime configuration.

    Environment variables take precedence over values in the .env file. Unknown
    variables are ignored so the same process can run on platforms that inject many
    unrelated variables (for example Render).
    """

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
        validate_default=True,
        env_ignore_empty=True,
    )

    readonly_database_url: SecretStr
    host: str = "0.0.0.0"
    port: int = Field(default=8050, ge=1, le=65535)
    dash_debug: bool = False
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=5, ge=0)
    db_pool_recycle_seconds: int = Field(default=300, ge=0)
    db_pool_timeout_seconds: int = Field(default=10, ge=0)
    db_connect_timeout_seconds: int = Field(default=10, ge=0)
    db_statement_timeout_ms: int = Field(default=15_000, ge=0)

    @field_validator("readonly_database_url")
    @classmethod
    def validate_readonly_database_url(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value().strip()
        if not raw or raw == EXAMPLE_URL:
            raise ValueError(
                "READONLY_DATABASE_URL is not set or still contains the example value. "
                "Copy dash-app/.env.example to dash-app/.env and paste the read-only "
                "Neon connection string."
            )

        try:
            url = make_url(raw)
        except (ArgumentError, ValueError):
            raise ValueError(
                "READONLY_DATABASE_URL is not a valid database URL."
            ) from None

        if url.drivername not in _POSTGRES_DRIVERS:
            raise ValueError(
                "READONLY_DATABASE_URL must be a PostgreSQL connection string."
            )
        return SecretStr(raw)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and validate settings once per process."""
    return Settings(_env_file=ENV_FILE)


def clear_settings_cache() -> None:
    """Forget the cached settings. Used in tests."""
    get_settings.cache_clear()


def database_url(settings: Settings | None = None) -> URL:
    """Return the SQLAlchemy URL using the psycopg3 driver."""
    settings = settings or get_settings()
    url = make_url(settings.readonly_database_url.get_secret_value())
    if url.drivername != "postgresql+psycopg":
        url = url.set(drivername="postgresql+psycopg")
    return url
