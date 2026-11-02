"""Annual statistics of the daily temperatures: per city and year, and per city.

Only complete years are used (365 or 366 days); the current year is excluded.
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

REFERENCE = (
    1961,
    1990,
)  # classic WMO climate normal: anomalies are measured against it
RECENT_YEARS = 10  # "the last years", compared with the reference
RECENT_TREND_FROM = 1975  # start of the sustained global warming
LESS_RELIABLE_BEFORE = 1950  # before, ERA5 has far fewer observations
PERCENTILES = {"p05": 0.05, "p25": 0.25, "p50": 0.50, "p75": 0.75, "p95": 0.95}


def read_database(db_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cities and daily values of the complete downloads, read-only.

    Returns `cities` (indexed by id, in download order) and `daily` with the columns
    city_id, date, t_mean, t_max, t_min and year.
    """
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cities = pd.read_sql(
            """SELECT c.* FROM cities c JOIN downloads d ON d.city_id = c.id
               WHERE d.status = 'complete' ORDER BY c.download_order""",
            connection,
        ).set_index("id")
        daily = pd.read_sql(
            """SELECT city_id, date, t_mean, t_max, t_min FROM daily
               WHERE city_id IN (SELECT city_id FROM downloads WHERE status = 'complete')""",
            connection,
        )
    finally:
        connection.close()
    daily["date"] = pd.to_datetime(daily["date"])
    daily["year"] = daily["date"].dt.year
    return cities, daily


def complete_years(
    daily: pd.DataFrame, first_year: int, last_year: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keeps the years of each city that have every day and are inside the period.

    Returns (kept daily values, dropped city-years with the days they had).
    """
    days = daily.groupby(["city_id", "year"]).size().rename("days").reset_index()
    leap = pd.to_datetime(days["year"].astype(str) + "-12-31").dt.day_of_year == 366
    days["expected"] = np.where(leap, 366, 365)
    valid = days["year"].between(first_year, last_year) & (
        days["days"] == days["expected"]
    )
    kept = daily.merge(days.loc[valid, ["city_id", "year"]], on=["city_id", "year"])
    return kept, days[~valid].reset_index(drop=True)


def annual_stats(
    daily: pd.DataFrame, reference: tuple[int, int] = REFERENCE
) -> pd.DataFrame:
    """Statistics per city and year, indexed by (city_id, year).

    | Column      | What it is |
    |-------------|------------|
    | mean        | annual mean of t_mean |
    | p05 … p95   | percentiles of t_mean among the days of the year |
    | max_mean    | annual mean of t_max (how hot the days are) |
    | min_mean    | annual mean of t_min (how warm the nights are) |
    | anomaly     | mean minus the mean of that city in the reference period |
    """
    groups = daily.groupby(["city_id", "year"])
    annual = groups.agg(
        mean=("t_mean", "mean"),
        max_mean=("t_max", "mean"),
        min_mean=("t_min", "mean"),
    )
    percentiles = groups["t_mean"].quantile(list(PERCENTILES.values())).unstack()
    percentiles.columns = list(PERCENTILES)
    annual = annual.join(percentiles)

    years = annual.index.get_level_values("year")
    in_reference = (years >= reference[0]) & (years <= reference[1])
    reference_mean = annual.loc[in_reference, "mean"].groupby("city_id").mean()
    annual["anomaly"] = (
        annual["mean"]
        - reference_mean.reindex(annual.index.get_level_values("city_id")).to_numpy()
    )
    return annual[["mean", *PERCENTILES, "max_mean", "min_mean", "anomaly"]]


def trend_per_decade(years, values) -> float:
    """Slope of the least-squares line (numpy.polyfit), in °C per decade."""
    slope, _ = np.polyfit(np.asarray(years), np.asarray(values), 1)
    return slope * 10


def summarize_city(
    table: pd.DataFrame,
    reference: tuple[int, int] = REFERENCE,
    recent_years: int = RECENT_YEARS,
    recent_trend_from: int = RECENT_TREND_FROM,
) -> pd.Series:
    """Summary of one city from its rows of `annual_stats` (indexed by year).

    - trend_decade: trend of the annual mean over every year, in °C per decade.
    - recent_trend: the same, only from `recent_trend_from`.
    - difference: mean of the last `recent_years` minus the mean of the reference period, i.e.
      "the last 10 years were X °C warmer than 1961–1990".
    - warmest_year: the year with the highest mean.
    """
    years = table.index.get_level_values("year")
    recent = years >= years.max() - recent_years + 1
    in_reference = (years >= reference[0]) & (years <= reference[1])
    since = years >= recent_trend_from
    return pd.Series(
        {
            "first_year": years.min(),
            "last_year": years.max(),
            "reference_mean": table.loc[in_reference, "mean"].mean(),
            "trend_decade": trend_per_decade(years, table["mean"]),
            "recent_trend": trend_per_decade(years[since], table.loc[since, "mean"]),
            "difference": table.loc[recent, "anomaly"].mean(),
            "warmest_year": years[table["mean"].to_numpy().argmax()],
        }
    )


def city_summary(annual: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """`summarize_city` for every city of `annual_stats`, one row per city."""
    summary = annual.groupby("city_id").apply(
        lambda table: summarize_city(table.droplevel("city_id"), **kwargs)
    )
    return summary.astype({"first_year": int, "last_year": int, "warmest_year": int})
