"""Read-only queries and DataFrame shaping for the climate database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from .db import fetch_df, ttl_cache

REFERENCE_PERIOD = (1961, 1990)
RECENT_YEARS = 10
RECENT_TREND_FROM = 1975
LESS_RELIABLE_BEFORE = 1950

CITY_CACHE_SECONDS = 3_600
DAILY_CACHE_SECONDS = 600
ANNUAL_CACHE_SECONDS = 1_800
STATUS_CACHE_SECONDS = 300

CITY_COLUMNS = [
    "id",
    "name",
    "country",
    "country_code",
    "continent",
    "latitude",
    "longitude",
    "cell_lat",
    "cell_lon",
    "population",
    "is_capital",
    "latitude_band",
    "coast_distance_km",
    "coastal",
    "priority",
    "download_order",
    "era5_lat",
    "era5_lon",
    "era5_elevation",
]
_CITY_SELECT = ", ".join(CITY_COLUMNS)

_DAILY_COLUMNS = ["city_id", "date", "t_mean", "t_max", "t_min"]
_ANNUAL_COLUMNS = [
    "year",
    "days",
    "mean",
    "p05",
    "p25",
    "p50",
    "p75",
    "p95",
    "max_mean",
    "min_mean",
    "anomaly",
]
_SUMMARY_COLUMNS = [
    "city_id",
    "first_year",
    "last_year",
    "reference_mean",
    "recent_mean",
    "difference",
    "trend_decade",
    "recent_trend",
    "warmest_year",
]
_STATUS_COLUMNS = [
    "city_id",
    "name",
    "country",
    "first_date",
    "last_date",
    "days",
    "expected_days",
    "missing_days",
    "days_behind",
    "complete",
]

_PERCENTILES = [
    ("p05", 0.05),
    ("p25", 0.25),
    ("p50", 0.50),
    ("p75", 0.75),
    ("p95", 0.95),
]
_PERCENTILE_SQL = ",\n        ".join(
    f"percentile_cont({value}) WITHIN GROUP (ORDER BY t_mean) AS {name}"
    for name, value in _PERCENTILES
)

_ANNUAL_STATS_SQL = f"""
SELECT
    EXTRACT(YEAR FROM date)::int AS year,
    COUNT(*)::int AS days,
    AVG(t_mean)::float8 AS mean,
    AVG(t_max)::float8 AS max_mean,
    AVG(t_min)::float8 AS min_mean,
    {_PERCENTILE_SQL}
FROM daily
WHERE city_id = :city_id
GROUP BY EXTRACT(YEAR FROM date)
ORDER BY year
"""

_ANNUAL_MEANS_SQL = """
SELECT
    city_id,
    EXTRACT(YEAR FROM date)::int AS year,
    COUNT(*)::int AS days,
    AVG(t_mean)::float8 AS mean
FROM daily
GROUP BY city_id, EXTRACT(YEAR FROM date)
ORDER BY city_id, year
"""

_CITY_STATUS_SQL = """
SELECT
    c.id AS city_id,
    c.name,
    c.country,
    MIN(d.date) AS first_date,
    MAX(d.date) AS last_date,
    COUNT(d.date)::int AS days,
    (MAX(d.date) - MIN(d.date) + 1)::int AS expected_days,
    (CURRENT_DATE - MAX(d.date))::int AS days_behind
FROM cities c
LEFT JOIN daily d ON d.city_id = c.id
GROUP BY c.id, c.name, c.country, c.download_order
ORDER BY c.download_order
"""


@dataclass(frozen=True)
class DatasetStatus:
    """Coverage and freshness of the whole database."""

    city_count: int
    row_count: int
    first_date: date | None
    latest_date: date | None
    cities: pd.DataFrame


@ttl_cache(CITY_CACHE_SECONDS, maxsize=1)
def list_cities() -> pd.DataFrame:
    """All cities, in download order."""
    frame = fetch_df(f"SELECT {_CITY_SELECT} FROM cities ORDER BY download_order")
    return _prepare_cities(frame)


def get_city(city_id: str) -> dict[str, Any] | None:
    """One city's metadata, or None when the identifier is unknown."""
    frame = list_cities()
    match = frame[frame["id"] == city_id]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


@ttl_cache(DAILY_CACHE_SECONDS, maxsize=128)
def city_daily(
    city_id: str, start: date | None = None, end: date | None = None
) -> pd.DataFrame:
    """Daily temperatures of one city, optionally limited to a date range."""
    clauses = ["city_id = :city_id"]
    params: dict[str, Any] = {"city_id": city_id}
    if start is not None:
        clauses.append("date >= :start")
        params["start"] = start
    if end is not None:
        clauses.append("date <= :end")
        params["end"] = end

    sql = (
        f"SELECT {', '.join(_DAILY_COLUMNS)} FROM daily "
        f"WHERE {' AND '.join(clauses)} ORDER BY date"
    )
    frame = fetch_df(sql, params, parse_dates=["date"])
    return _prepare_daily(frame)


@ttl_cache(ANNUAL_CACHE_SECONDS, maxsize=256)
def city_annual_stats(city_id: str) -> pd.DataFrame:
    """Annual aggregates of one city, with anomalies against the reference period."""
    frame = fetch_df(_ANNUAL_STATS_SQL, {"city_id": city_id})
    return _prepare_annual_stats(frame)


@ttl_cache(ANNUAL_CACHE_SECONDS, maxsize=1)
def city_summaries() -> pd.DataFrame:
    """One row per city with reference, recent, trend and warmest-year metrics."""
    cities = list_cities()
    annual = _complete_years(_annual_means_all())

    rows = []
    for city_id, group in annual.groupby("city_id", sort=False):
        row = _summarize_city(group)
        row["city_id"] = city_id
        rows.append(row)

    summary = pd.DataFrame(rows, columns=_SUMMARY_COLUMNS)
    result = cities.merge(summary, left_on="id", right_on="city_id", how="left")
    result = result.drop(columns=["city_id"])
    for column in ("first_year", "last_year", "warmest_year"):
        result[column] = result[column].astype("Int64")
    return result


def data_status() -> DatasetStatus:
    """Coverage and freshness of every city, plus database-wide totals."""
    cities = _city_status()
    with_data = cities.dropna(subset=["first_date"])
    return DatasetStatus(
        city_count=len(cities),
        row_count=int(cities["days"].fillna(0).sum()),
        first_date=(
            with_data["first_date"].min().date() if not with_data.empty else None
        ),
        latest_date=(
            with_data["last_date"].max().date() if not with_data.empty else None
        ),
        cities=cities.copy(),
    )


@ttl_cache(ANNUAL_CACHE_SECONDS, maxsize=1)
def _annual_means_all() -> pd.DataFrame:
    frame = fetch_df(_ANNUAL_MEANS_SQL)
    if frame.empty:
        return pd.DataFrame(columns=["city_id", "year", "days", "mean"])
    frame["year"] = frame["year"].astype(int)
    frame["days"] = frame["days"].astype(int)
    frame["mean"] = frame["mean"].astype(float)
    return frame


@ttl_cache(STATUS_CACHE_SECONDS, maxsize=1)
def _city_status() -> pd.DataFrame:
    frame = fetch_df(_CITY_STATUS_SQL)
    return _prepare_status(frame)


def _prepare_cities(frame: pd.DataFrame) -> pd.DataFrame:
    for column in ("is_capital", "coastal"):
        if column in frame:
            frame[column] = frame[column].fillna(0).astype(bool)
    return frame


def _prepare_daily(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=_DAILY_COLUMNS)
    frame["date"] = pd.to_datetime(frame["date"])
    for column in ("t_mean", "t_max", "t_min"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)
    return frame


def _prepare_annual_stats(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=_ANNUAL_COLUMNS)

    frame["year"] = frame["year"].astype(int)
    frame["days"] = frame["days"].astype(int)
    for column in ("mean", "p05", "p25", "p50", "p75", "p95", "max_mean", "min_mean"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)

    in_reference = frame["year"].between(*REFERENCE_PERIOD)
    reference_mean = frame.loc[in_reference, "mean"].mean()
    frame["anomaly"] = frame["mean"] - reference_mean
    return frame[_ANNUAL_COLUMNS]


def _prepare_status(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=_STATUS_COLUMNS)

    frame["first_date"] = pd.to_datetime(frame["first_date"])
    frame["last_date"] = pd.to_datetime(frame["last_date"])
    for column in ("days", "expected_days", "days_behind"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
    frame["missing_days"] = frame["expected_days"] - frame["days"]
    frame["complete"] = (frame["days"].fillna(0) > 0) & (
        frame["missing_days"].fillna(0) == 0
    )
    return frame[_STATUS_COLUMNS]


def _complete_years(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    expected = pd.to_datetime(frame["year"].astype(str) + "-12-31").dt.dayofyear
    return frame.loc[frame["days"] == expected].copy()


def _trend_per_decade(years: pd.Series, values: pd.Series) -> float:
    if len(years) < 2:
        return float("nan")
    slope, _ = np.polyfit(years.to_numpy(dtype=float), values.to_numpy(dtype=float), 1)
    return float(slope * 10)


def _summarize_city(group: pd.DataFrame) -> dict[str, Any]:
    years = group["year"].astype(int)
    values = group["mean"].astype(float)
    latest = int(years.max())

    in_reference = group["year"].between(*REFERENCE_PERIOD)
    recent = group["year"] >= latest - RECENT_YEARS + 1
    since_recent_trend = group["year"] >= RECENT_TREND_FROM

    reference_mean = group.loc[in_reference, "mean"].mean()
    recent_mean = group.loc[recent, "mean"].mean()
    warmest_year = int(years.iloc[values.to_numpy().argmax()])

    return {
        "first_year": int(years.min()),
        "last_year": latest,
        "reference_mean": float(reference_mean),
        "recent_mean": float(recent_mean),
        "difference": float(recent_mean - reference_mean),
        "trend_decade": _trend_per_decade(years, values),
        "recent_trend": _trend_per_decade(
            group.loc[since_recent_trend, "year"],
            group.loc[since_recent_trend, "mean"],
        ),
        "warmest_year": warmest_year,
    }
