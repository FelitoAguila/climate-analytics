"""Offline tests for the read-only data layer."""

from __future__ import annotations

import calendar
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest
from dash_app import settings
from dash_app.data import db, queries
from dash_app.errors import DataUnavailable
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture(autouse=True)
def _isolated_data_layer():
    db.reset_engine()
    db.clear_data_caches()
    settings.clear_settings_cache()
    yield
    db.reset_engine()
    db.clear_data_caches()
    settings.clear_settings_cache()


def _city_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "phoenix-us",
                "name": "Phoenix",
                "country": "United States of America",
                "country_code": "US",
                "continent": "North America",
                "latitude": 33.5419,
                "longitude": -112.0719,
                "cell_lat": 33.5,
                "cell_lon": -112.0,
                "population": 3551000,
                "is_capital": 0,
                "latitude_band": "subtropical_north",
                "coast_distance_km": 271,
                "coastal": 0,
                "priority": 1,
                "download_order": 1,
                "era5_lat": 33.5,
                "era5_lon": -112.0,
                "era5_elevation": 300.0,
            },
            {
                "id": "antananarivo-mg",
                "name": "Antananarivo",
                "country": "Madagascar",
                "country_code": "MG",
                "continent": "Africa",
                "latitude": -18.9147,
                "longitude": 47.5147,
                "cell_lat": -19.0,
                "cell_lon": 47.5,
                "population": 1697000,
                "is_capital": 1,
                "latitude_band": "tropical_south",
                "coast_distance_km": 162,
                "coastal": 0,
                "priority": 1,
                "download_order": 2,
                "era5_lat": -19.0,
                "era5_lon": 47.5,
                "era5_elevation": 1280.0,
            },
        ]
    )


def _days(year: int) -> int:
    return 366 if calendar.isleap(year) else 365


def test_engine_uses_settings_and_read_only_session(monkeypatch):
    captured = {}
    fake_engine = SimpleNamespace(dispose=lambda: None)
    fake_settings = settings.Settings(
        _env_file=None,
        readonly_database_url="postgresql://user:pass@host/db",
        db_pool_size=3,
        db_max_overflow=4,
        db_pool_recycle_seconds=120,
        db_pool_timeout_seconds=7,
        db_connect_timeout_seconds=8,
        db_statement_timeout_ms=9_000,
    )

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return fake_engine

    monkeypatch.setattr(db, "create_engine", fake_create_engine)
    monkeypatch.setattr(db, "get_settings", lambda: fake_settings)

    assert db.get_engine() is fake_engine
    assert captured["url"].drivername == "postgresql+psycopg"
    assert captured["kwargs"]["pool_size"] == 3
    assert captured["kwargs"]["max_overflow"] == 4
    assert captured["kwargs"]["pool_recycle"] == 120
    assert captured["kwargs"]["pool_timeout"] == 7
    connect_args = captured["kwargs"]["connect_args"]
    assert connect_args["application_name"] == "dash-app"
    assert connect_args["connect_timeout"] == 8
    assert "default_transaction_read_only=on" in connect_args["options"]
    assert "statement_timeout=9000" in connect_args["options"]


def test_fetch_df_wraps_sqlalchemy_errors(monkeypatch):
    def fail():
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(db, "get_engine", fail)
    with pytest.raises(DataUnavailable):
        db.fetch_df("SELECT 1")


def test_fetch_df_wraps_pandas_database_errors(monkeypatch):
    class Connection:
        def __enter__(self):
            return object()

        def __exit__(self, *args):
            return False

    class Engine:
        def connect(self):
            return Connection()

    def fail(*args, **kwargs):
        raise pd.errors.DatabaseError("boom")

    monkeypatch.setattr(db, "get_engine", lambda: Engine())
    monkeypatch.setattr(db.pd, "read_sql_query", fail)
    with pytest.raises(DataUnavailable):
        db.fetch_df("SELECT 1")


def test_list_cities_cached_and_returns_copies(monkeypatch):
    calls = {"count": 0}

    def fake_fetch(*args, **kwargs):
        calls["count"] += 1
        return _city_frame()

    monkeypatch.setattr(queries, "fetch_df", fake_fetch)

    first = queries.list_cities()
    first.loc[0, "name"] = "changed"
    second = queries.list_cities()

    assert calls["count"] == 1
    assert second.loc[0, "name"] == "Phoenix"
    assert bool(second.loc[0, "is_capital"]) is False
    assert bool(second.loc[1, "is_capital"]) is True


def test_get_city(monkeypatch):
    monkeypatch.setattr(queries, "list_cities", _city_frame)
    assert queries.get_city("antananarivo-mg")["name"] == "Antananarivo"
    assert queries.get_city("unknown") is None


def test_city_daily_parameters_and_dates(monkeypatch):
    captured = {}

    def fake_fetch(sql, params=None, *, parse_dates=None):
        captured["sql"] = sql
        captured["params"] = params
        captured["parse_dates"] = parse_dates
        return pd.DataFrame(
            {
                "city_id": ["phoenix-us"],
                "date": ["2020-01-01"],
                "t_mean": [15.0],
                "t_max": [22.0],
                "t_min": [8.0],
            }
        )

    monkeypatch.setattr(queries, "fetch_df", fake_fetch)
    frame = queries.city_daily(
        "phoenix-us", start=date(2020, 1, 1), end=date(2020, 12, 31)
    )

    assert "date >= :start" in captured["sql"]
    assert "date <= :end" in captured["sql"]
    assert captured["params"] == {
        "city_id": "phoenix-us",
        "start": date(2020, 1, 1),
        "end": date(2020, 12, 31),
    }
    assert captured["parse_dates"] == ["date"]
    assert str(frame["date"].dtype).startswith("datetime64")


def test_city_annual_stats_computes_anomaly(monkeypatch):
    def fake_fetch(*args, **kwargs):
        return pd.DataFrame(
            {
                "year": [1961, 1990, 1991],
                "days": [365, 365, 365],
                "mean": [12.0, 14.0, 16.0],
                "max_mean": [20.0, 22.0, 24.0],
                "min_mean": [4.0, 6.0, 8.0],
                "p05": [1.0, 2.0, 3.0],
                "p25": [5.0, 6.0, 7.0],
                "p50": [12.0, 14.0, 16.0],
                "p75": [18.0, 20.0, 22.0],
                "p95": [25.0, 27.0, 29.0],
            }
        )

    monkeypatch.setattr(queries, "fetch_df", fake_fetch)
    frame = queries.city_annual_stats("city")

    assert list(frame.columns) == queries._ANNUAL_COLUMNS
    anomaly = frame.loc[frame["year"] == 1991, "anomaly"].iloc[0]
    assert anomaly == pytest.approx(3.0)


def test_complete_years_filters_incomplete_years():
    frame = pd.DataFrame(
        {
            "year": [2020, 2021],
            "days": [365, 365],
            "mean": [1.0, 2.0],
        }
    )
    kept = queries._complete_years(frame)
    assert kept["year"].tolist() == [2021]


def test_city_summaries(monkeypatch):
    annual = pd.DataFrame(
        {
            "city_id": ["phoenix-us"] * 4,
            "year": [1961, 1990, 2016, 2025],
            "days": [_days(year) for year in (1961, 1990, 2016, 2025)],
            "mean": [10.0, 12.0, 15.0, 16.0],
        }
    )
    monkeypatch.setattr(queries, "list_cities", _city_frame)
    monkeypatch.setattr(queries, "_annual_means_all", lambda: annual)

    frame = queries.city_summaries()
    row = frame.loc[frame["id"] == "phoenix-us"].iloc[0]

    assert row["first_year"] == 1961
    assert row["last_year"] == 2025
    assert row["reference_mean"] == pytest.approx(11.0)
    assert row["recent_mean"] == pytest.approx(15.5)
    assert row["difference"] == pytest.approx(4.5)
    assert row["warmest_year"] == 2025


def test_data_status(monkeypatch):
    raw = pd.DataFrame(
        {
            "city_id": ["phoenix-us", "empty-city"],
            "name": ["Phoenix", "Empty"],
            "country": ["US", "XX"],
            "first_date": [pd.Timestamp("1940-01-01"), pd.NaT],
            "last_date": [pd.Timestamp("2025-12-31"), pd.NaT],
            "days": [31001, 0],
            "expected_days": [31001, None],
            "days_behind": [1, None],
        }
    )
    prepared = queries._prepare_status(raw)
    monkeypatch.setattr(queries, "_city_status", lambda: prepared)

    status = queries.data_status()

    assert status.city_count == 2
    assert status.row_count == 31001
    assert status.first_date == date(1940, 1, 1)
    assert status.latest_date == date(2025, 12, 31)
    assert status.cities is not prepared
    assert bool(status.cities.loc[0, "complete"]) is True
    assert bool(status.cities.loc[1, "complete"]) is False
