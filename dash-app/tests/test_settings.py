"""Tests for validated application settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dash_app import settings
from dash_app.app import create_app

VALID_URL = "postgresql://climate_reader:secret@db.example/neondb?sslmode=require"


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    settings.clear_settings_cache()
    yield
    settings.clear_settings_cache()


def test_missing_url_is_rejected(monkeypatch):
    monkeypatch.delenv("READONLY_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="readonly_database_url"):
        settings.Settings(_env_file=None)


def test_create_app_validates_settings(monkeypatch, tmp_path):
    monkeypatch.delenv("READONLY_DATABASE_URL", raising=False)
    monkeypatch.setattr(settings, "ENV_FILE", tmp_path / "missing.env")
    settings.clear_settings_cache()
    with pytest.raises(ValidationError, match="readonly_database_url"):
        create_app()


def test_example_url_is_rejected():
    with pytest.raises(ValidationError, match="example value"):
        settings.Settings(
            _env_file=None,
            readonly_database_url=settings.EXAMPLE_URL,
        )


def test_non_postgres_url_is_rejected():
    with pytest.raises(ValidationError, match="PostgreSQL"):
        settings.Settings(_env_file=None, readonly_database_url="sqlite:///climate.db")


def test_database_url_uses_psycopg3_driver():
    config = settings.Settings(_env_file=None, readonly_database_url=VALID_URL)
    url = settings.database_url(config)
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "secret"


def test_secret_is_masked():
    config = settings.Settings(_env_file=None, readonly_database_url=VALID_URL)
    assert "secret" not in repr(config)
    assert "secret" not in str(config)
    assert config.readonly_database_url.get_secret_value() == VALID_URL


def test_types_are_coerced():
    config = settings.Settings(
        _env_file=None,
        readonly_database_url=VALID_URL,
        port="9000",
        dash_debug="true",
        db_pool_size="7",
    )
    assert config.port == 9000
    assert config.dash_debug is True
    assert config.db_pool_size == 7


def test_invalid_bounds_are_rejected():
    with pytest.raises(ValidationError):
        settings.Settings(_env_file=None, readonly_database_url=VALID_URL, port=70000)
    with pytest.raises(ValidationError):
        settings.Settings(
            _env_file=None, readonly_database_url=VALID_URL, db_pool_size=0
        )


def test_unknown_environment_variables_are_ignored(monkeypatch):
    monkeypatch.setenv("SOME_UNRELATED_PLATFORM_VARIABLE", "value")
    config = settings.Settings(_env_file=None, readonly_database_url=VALID_URL)
    assert config.readonly_database_url.get_secret_value() == VALID_URL


def test_env_file_is_loaded(monkeypatch, tmp_path):
    monkeypatch.delenv("READONLY_DATABASE_URL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "READONLY_DATABASE_URL=postgresql://file:file@host/file\n",
        encoding="utf-8",
    )

    config = settings.Settings(_env_file=env_file)
    assert (
        config.readonly_database_url.get_secret_value()
        == "postgresql://file:file@host/file"
    )


def test_environment_overrides_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "READONLY_DATABASE_URL=postgresql://file:file@host/file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("READONLY_DATABASE_URL", "postgresql://env:env@host/env")

    config = settings.Settings(_env_file=env_file)
    assert (
        config.readonly_database_url.get_secret_value()
        == "postgresql://env:env@host/env"
    )


def test_get_settings_uses_configured_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("READONLY_DATABASE_URL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "READONLY_DATABASE_URL=postgresql://file:file@host/file\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "ENV_FILE", env_file)

    config = settings.get_settings()
    assert (
        config.readonly_database_url.get_secret_value()
        == "postgresql://file:file@host/file"
    )
