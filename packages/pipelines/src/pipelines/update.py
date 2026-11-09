"""Adds the newest days to Neon. Meant to run every day: `uv run update-neon`.

`--limit N` updates only the first N cities. For each city:

1. Reads its last date and coordinates from the database, so it needs no local data.
2. Asks the API from `WINDOW_DAYS` before that date until today.
3. Keeps the days up to the first one with an empty value. ERA5 arrives about a week late, and
   the newest day can come half empty (a mean without maximum or minimum).
4. Validates them like a download and checks that the API still uses the same ERA5 cell.
5. Writes only the days that are new or changed, in one transaction.

The window repeats recent days because ERA5 can correct them. Running it again changes nothing
if the API has nothing new. A city that fails does not stop the others, but the program ends
with an error so that a scheduled run reports it.
"""

import argparse
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from functools import partial

import requests

from pipelines.download import (
    DailyLimitReached,
    DownloadConfig,
    DownloadError,
    days_between,
    fetch_with_retries,
    open_db,
    usage_24h,
    validate,
)
from pipelines.neon import connect, database_url
from pipelines.open_meteo import DAILY_VARIABLES, build_params, request_cost

WINDOW_DAYS = 30
PAUSE_SECONDS = (
    1  # between cities: even the first update stays under 600 calls a minute
)
SAME_VALUE_TOLERANCE = 0.01  # °C; the database keeps 4-byte numbers with one decimal
SAME_CELL_TOLERANCE = 0.001  # degrees

UPSERT = """
INSERT INTO daily (city_id, date, t_mean, t_max, t_min) VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (city_id, date) DO UPDATE
SET t_mean = EXCLUDED.t_mean, t_max = EXCLUDED.t_max, t_min = EXCLUDED.t_min
"""


@dataclass
class City:
    id: str
    latitude: float
    longitude: float
    era5_lat: float
    era5_lon: float
    last_date: date


@dataclass
class Changes:
    """Days to write for one city, and how much the days already stored have moved."""

    new: list[tuple]
    changed: list[tuple]
    largest_change: float


def read_cities(connection) -> list[City]:
    """Cities of the database with their last day, in download order."""
    rows = connection.execute(
        """SELECT c.id, c.latitude, c.longitude, c.era5_lat, c.era5_lon,
                  (SELECT MAX(d.date) FROM daily d WHERE d.city_id = c.id)
           FROM cities c ORDER BY c.download_order"""
    ).fetchall()
    return [City(*row) for row in rows if row[-1] is not None]


def complete_days(daily: dict) -> dict:
    """The days of a response up to the first one with an empty value."""
    columns = [daily.get(variable, []) for variable in DAILY_VARIABLES]
    n_days = 0
    for values in zip(*columns, strict=False):
        if None in values:
            break
        n_days += 1
    return {
        "time": daily.get("time", [])[:n_days],
        **{
            variable: column[:n_days]
            for variable, column in zip(DAILY_VARIABLES, columns)
        },
    }


def fetch_days(
    usage,
    city: City,
    today: date,
    config: DownloadConfig,
    log: Callable,
    get: Callable = requests.get,
) -> list[tuple]:
    """Complete days of the window as (date, t_mean, t_max, t_min). `usage` records the calls."""
    start = str(city.last_date - timedelta(days=WINDOW_DAYS))
    end = str(today)
    payload = fetch_with_retries(
        usage,
        city.id,
        build_params(city.latitude, city.longitude, start, end),
        request_cost(days_between(start, end)),
        config,
        log,
        get,
    )
    moved = max(
        abs(payload["latitude"] - city.era5_lat),
        abs(payload["longitude"] - city.era5_lon),
    )
    if moved > SAME_CELL_TOLERANCE:
        raise DownloadError(
            f"ERA5 cell changed: {payload['latitude']}, {payload['longitude']} "
            f"instead of {city.era5_lat}, {city.era5_lon}"
        )

    daily = complete_days(payload.get("daily", {}))
    if not daily["time"]:
        raise DownloadError(f"no complete days from {start}")
    problems = validate({"daily": daily}, start, daily["time"][-1])
    if problems:
        raise DownloadError("; ".join(problems))
    return [
        (date.fromisoformat(day), *values)
        for day, *values in zip(
            daily["time"],
            *(daily[variable] for variable in DAILY_VARIABLES),
            strict=True,
        )
    ]


def compare(days: list[tuple], stored: dict[date, tuple]) -> Changes:
    """Separates the days that are new, or different from what is stored, from the rest."""
    new, changed = [], []
    largest_change = 0.0
    for day in days:
        values = stored.get(day[0])
        if values is None:
            new.append(day)
            continue
        change = max(abs(a - b) for a, b in zip(day[1:], values, strict=True))
        if change > SAME_VALUE_TOLERANCE:
            changed.append(day)
            largest_change = max(largest_change, change)
    return Changes(new, changed, largest_change)


def stored_days(connection, city: City) -> dict[date, tuple]:
    """Values already in the database for the days of the window."""
    rows = connection.execute(
        "SELECT date, t_mean, t_max, t_min FROM daily WHERE city_id = %s AND date >= %s",
        (city.id, city.last_date - timedelta(days=WINDOW_DAYS)),
    ).fetchall()
    return {row[0]: row[1:] for row in rows}


def write_days(connection, city_id: str, days: list[tuple]) -> None:
    """Writes the days of one city, all or nothing."""
    if not days:
        return
    with connection.transaction(), connection.cursor() as cursor:
        cursor.executemany(UPSERT, [(city_id, *day) for day in days])


@dataclass
class Summary:
    """What an update did, to log it or show it in Dagster."""

    new_days: int = 0
    changed_days: int = 0
    largest_change: float = 0.0
    api_calls: float = 0.0
    failed: list[str] = field(default_factory=list)
    complete_until: date | None = None  # the earliest last day of the cities updated


def update(connection, cities: list[City], today: date, log=print) -> Summary:
    """Updates each city and logs what changed. Returns a summary."""
    # fetch_with_retries records every call in a database: here it only lasts for this run
    usage = open_db(":memory:")
    config = DownloadConfig()
    summary = Summary()
    for position, city in enumerate(cities, start=1):
        try:
            days = fetch_days(usage, city, today, config, log)
        except DailyLimitReached as error:
            log(f"API daily limit reached ({error}). Stopping.")
            summary.failed.extend(c.id for c in cities[position - 1 :])
            break
        except DownloadError as error:
            log(f"[{position}/{len(cities)}] {city.id}: FAILED, {error}")
            summary.failed.append(city.id)
            continue

        changes = compare(days, stored_days(connection, city))
        write_days(connection, city.id, changes.new + changes.changed)
        summary.new_days += len(changes.new)
        summary.changed_days += len(changes.changed)
        summary.largest_change = max(summary.largest_change, changes.largest_change)
        last_day = days[-1][0]
        if summary.complete_until is None or last_day < summary.complete_until:
            summary.complete_until = last_day
        log(
            f"[{position}/{len(cities)}] {city.id}: {len(changes.new)} new, "
            f"{len(changes.changed)} changed, complete until {days[-1][0]}"
        )
        if position < len(cities):
            time.sleep(PAUSE_SECONDS)

    summary.api_calls = usage_24h(usage)
    usage.close()
    log(
        f"Done: {summary.new_days:,} new days, {summary.changed_days:,} changed "
        f"(largest change {summary.largest_change:.2f} °C), "
        f"{summary.api_calls:.0f} API calls, {len(summary.failed)} cities failed"
    )
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Adds the newest days to Neon.")
    parser.add_argument(
        "--limit", type=int, help="update only the first N cities (to test)"
    )
    args = parser.parse_args(argv)

    url = database_url()
    with connect(url) as connection:
        cities = read_cities(connection)[: args.limit]
        # flush: a scheduled run writes to a file, and it would show nothing until the end
        log = partial(print, flush=True)
        summary = update(connection, cities, datetime.now(UTC).date(), log)
    if summary.failed:
        raise SystemExit(f"Could not update: {', '.join(summary.failed)}")
