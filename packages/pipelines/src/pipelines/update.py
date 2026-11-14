"""Adds the newest days to Neon. Meant to run every day: `uv run update-neon`.

`--limit N` updates only the first N cities. For each city:

1. Reads its last date and coordinates from the database, so it needs no local data.
2. Asks the API from `WINDOW_DAYS` before that date until today.
   Cities with the same last date share one request (up to `BATCH_SIZE` of them): from GitHub's
   machines the API holds about one request in six for minutes, so 140 separate requests could
   take longer than the run allows. The API counts the calls per city, so this costs the same.
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
from dataclasses import dataclass
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
BATCH_SIZE = 50  # cities per request: a short URL, and ~50 calls, far from 600 a minute
PAUSE_SECONDS = 1  # between requests
TIMEOUT_SECONDS = 60  # per request; an answer normally takes a few seconds
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


def batches(cities: list[City]) -> list[list[City]]:
    """Groups of up to `BATCH_SIZE` cities with the same last date, in their order."""
    by_date: dict[date, list[City]] = {}
    for city in cities:
        by_date.setdefault(city.last_date, []).append(city)
    return [
        group[i : i + BATCH_SIZE]
        for group in by_date.values()
        for i in range(0, len(group), BATCH_SIZE)
    ]


def window_start(city: City) -> str:
    return str(city.last_date - timedelta(days=WINDOW_DAYS))


def fetch_batch(
    usage,
    cities: list[City],
    today: date,
    config: DownloadConfig,
    log: Callable,
    get: Callable = requests.get,
) -> list[dict]:
    """One request for cities with the same last date: one response per city, in their order.

    `usage` records the calls."""
    start, end = window_start(cities[0]), str(today)
    params = build_params(cities[0].latitude, cities[0].longitude, start, end)
    params["latitude"] = ",".join(str(city.latitude) for city in cities)
    params["longitude"] = ",".join(str(city.longitude) for city in cities)
    payload = fetch_with_retries(
        usage,
        cities[0].id if len(cities) == 1 else f"{len(cities)} cities",
        params,
        len(cities) * request_cost(days_between(start, end)),
        config,
        log,
        get,
    )
    # With one location the API answers an object; with several, a list
    payloads = payload if isinstance(payload, list) else [payload]
    if len(payloads) != len(cities):
        raise DownloadError(
            f"{len(payloads)} results for {len(cities)} cities in one request"
        )
    return payloads


def city_days(city: City, payload: dict) -> list[tuple]:
    """Complete days of the window in one city's response, as (date, t_mean, t_max, t_min)."""
    moved = max(
        abs(payload["latitude"] - city.era5_lat),
        abs(payload["longitude"] - city.era5_lon),
    )
    if moved > SAME_CELL_TOLERANCE:
        raise DownloadError(
            f"ERA5 cell changed: {payload['latitude']}, {payload['longitude']} "
            f"instead of {city.era5_lat}, {city.era5_lon}"
        )

    start = window_start(city)
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


def fetch_days(
    usage,
    city: City,
    today: date,
    config: DownloadConfig,
    log: Callable,
    get: Callable = requests.get,
) -> list[tuple]:
    """Complete days of the window for one city, with a request of its own."""
    return city_days(city, fetch_batch(usage, [city], today, config, log, get)[0])


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


def update(
    connection,
    cities: list[City],
    today: date,
    log=print,
    get: Callable = requests.get,
) -> list[str]:
    """Updates each city and logs what changed. Returns the cities that failed."""
    # fetch_with_retries records every call in a database: here it only lasts for this run
    usage = open_db(":memory:")
    config = DownloadConfig(timeout_seconds=TIMEOUT_SECONDS)
    failed, n_new, n_changed, largest_change = [], 0, 0, 0.0
    position = 0
    groups = batches(cities)
    for number, batch in enumerate(groups):
        if number:
            time.sleep(PAUSE_SECONDS)
        try:
            payloads = fetch_batch(usage, batch, today, config, log, get)
        except DailyLimitReached as error:
            log(f"API daily limit reached ({error}). Stopping.")
            failed.extend(c.id for group in groups[number:] for c in group)
            break
        except DownloadError as error:
            log(f"Request for {len(batch)} cities FAILED: {error}")
            failed.extend(c.id for c in batch)
            position += len(batch)
            continue

        for city, payload in zip(batch, payloads, strict=True):
            position += 1
            try:
                days = city_days(city, payload)
            except DownloadError as error:
                log(f"[{position}/{len(cities)}] {city.id}: FAILED, {error}")
                failed.append(city.id)
                continue
            changes = compare(days, stored_days(connection, city))
            write_days(connection, city.id, changes.new + changes.changed)
            n_new += len(changes.new)
            n_changed += len(changes.changed)
            largest_change = max(largest_change, changes.largest_change)
            log(
                f"[{position}/{len(cities)}] {city.id}: {len(changes.new)} new, "
                f"{len(changes.changed)} changed, complete until {days[-1][0]}"
            )

    log(
        f"Done: {n_new:,} new days, {n_changed:,} changed "
        f"(largest change {largest_change:.2f} °C), {usage_24h(usage):.0f} API calls, "
        f"{len(failed)} cities failed"
    )
    usage.close()
    return failed


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
        failed = update(connection, cities, datetime.now(UTC).date(), log)
    if failed:
        raise SystemExit(f"Could not update: {', '.join(failed)}")
