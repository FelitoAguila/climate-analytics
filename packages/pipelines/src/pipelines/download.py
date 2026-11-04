"""Resumable download of the daily temperatures of every city into SQLite.

- Before each city the batch checks a **budget** (the calls spent in the last 24 h, which we
  record ourselves in the `usage` table, because the API does not report them) and waits a
  **pause** since the last request (one full city is above the per-minute limit).
- Each city is downloaded, **validated** and saved **in one transaction**: either all its days
  are saved and it becomes `complete`, or nothing is saved.
- **Resumable:** running the batch again only requests the cities that are not `complete`.

Tables:

| Table       | One row per…   | What for |
|-------------|----------------|----------|
| `cities`    | city           | copy of data/cities.csv + the ERA5 cell returned by the API |
| `downloads` | city           | status (pending / complete / error), attempts, last error |
| `daily`     | city and day   | t_mean, t_max, t_min; primary key (city_id, date) |
| `usage`     | API request    | time, city, calls spent, HTTP status: our quota counter |
"""

import sqlite3
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from itertools import repeat
from pathlib import Path

import pandas as pd
import requests

from pipelines.open_meteo import (
    ARCHIVE_URL,
    DAILY_VARIABLES,
    build_params,
    request_cost,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS cities (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    country           TEXT,
    country_code      TEXT,
    continent         TEXT,
    latitude          REAL NOT NULL,
    longitude         REAL NOT NULL,
    cell_lat          REAL,
    cell_lon          REAL,
    population        INTEGER,
    is_capital        INTEGER,
    latitude_band     TEXT,
    coast_distance_km INTEGER,
    coastal           INTEGER,
    priority          INTEGER,
    download_order    INTEGER,
    era5_lat          REAL,      -- cell returned by the API
    era5_lon          REAL,
    era5_elevation    REAL
);

CREATE TABLE IF NOT EXISTS downloads (
    city_id       TEXT PRIMARY KEY REFERENCES cities(id),
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'complete', 'error')),
    attempts      INTEGER NOT NULL DEFAULT 0,
    last_error    TEXT,
    warning       TEXT,
    start_date    TEXT,
    end_date      TEXT,
    n_days        INTEGER,
    downloaded_at TEXT
);

CREATE TABLE IF NOT EXISTS daily (
    city_id TEXT NOT NULL REFERENCES cities(id),
    date    TEXT NOT NULL,           -- 'YYYY-MM-DD'
    t_mean  REAL,
    t_max   REAL,
    t_min   REAL,
    PRIMARY KEY (city_id, date)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    at          TEXT NOT NULL,       -- UTC time, ISO format
    city_id     TEXT,
    calls       REAL NOT NULL,
    http_status INTEGER,
    detail      TEXT
);
"""

# cities.csv column -> cities table column ("order" is a reserved word in SQL)
CITY_COLUMNS = {
    "id": "id",
    "name": "name",
    "country": "country",
    "country_code": "country_code",
    "continent": "continent",
    "latitude": "latitude",
    "longitude": "longitude",
    "cell_lat": "cell_lat",
    "cell_lon": "cell_lon",
    "population": "population",
    "is_capital": "is_capital",
    "latitude_band": "latitude_band",
    "coast_distance_km": "coast_distance_km",
    "coastal": "coastal",
    "priority": "priority",
    "order": "download_order",
}


@dataclass
class DownloadConfig:
    daily_budget: float = 9_000  # calls in 24 h (the real limit is 10,000)
    pause_minutes: float = (
        9  # between requests: respects the per-minute and hourly limits
    )
    max_retries: int = 3  # per request (429, 5xx, network errors, empty 200)
    max_attempts_per_city: int = 3  # a city that fails 3 times is no longer requested
    timeout_seconds: float = 120


class DailyLimitReached(Exception):
    """The API answered with its daily limit: the batch must stop."""


class DownloadError(Exception):
    """A city could not be downloaded (the batch goes on with the next one)."""


Log = Callable[[str], None]


def file_logger(path: Path) -> Log:
    """A `log` function that prints each message with the time and appends it to `path`."""

    def log(message: str) -> None:
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {message}"
        print(line, flush=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    return log


def utc_now() -> str:
    """Current UTC time in ISO format: all rows use it, so they compare as text in SQL."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1


def read_cities_csv(path: Path) -> pd.DataFrame:
    # keep_default_na=False: otherwise pandas reads Namibia's code ("NA") as an empty value
    return pd.read_csv(path, keep_default_na=False)


def open_db(path: Path) -> sqlite3.Connection:
    """Opens (or creates) the database. WAL mode lets other programs read while it writes."""
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection


def load_cities(connection: sqlite3.Connection, cities: pd.DataFrame) -> list[str]:
    """Inserts or updates the cities of the CSV; new ones start as 'pending'.

    The era5_* columns and the status of past downloads are not touched. Cities that are no
    longer in the CSV and have no data are deleted, so the batch does not request them.
    Returns the deleted ids.
    """
    db_columns = list(CITY_COLUMNS.values())
    columns = ", ".join(db_columns)
    holes = ", ".join("?" for _ in db_columns)
    update = ", ".join(f"{c} = excluded.{c}" for c in db_columns if c != "id")
    rows = cities[list(CITY_COLUMNS)].astype(object).itertuples(index=False, name=None)
    with connection:  # one transaction
        connection.executemany(
            f"INSERT INTO cities ({columns}) VALUES ({holes}) "
            f"ON CONFLICT(id) DO UPDATE SET {update}",
            rows,
        )
        connection.executemany(
            "INSERT OR IGNORE INTO downloads (city_id) VALUES (?)",
            [(city_id,) for city_id in cities["id"]],
        )
        # Cities that left the CSV are only deleted if they have no saved day:
        # downloaded data are never lost
        csv_ids = list(cities["id"])
        id_holes = ", ".join("?" for _ in csv_ids)
        leftovers = [
            row[0]
            for row in connection.execute(
                f"""SELECT c.id FROM cities c JOIN downloads d ON d.city_id = c.id
                    WHERE c.id NOT IN ({id_holes})
                      AND d.status != 'complete'
                      AND NOT EXISTS (SELECT 1 FROM daily x WHERE x.city_id = c.id)""",
                csv_ids,
            )
        ]
        for table, column in (("downloads", "city_id"), ("cities", "id")):
            connection.executemany(
                f"DELETE FROM {table} WHERE {column} = ?", [(i,) for i in leftovers]
            )
    return leftovers


def record_usage(connection, city_id, calls, http_status, detail=None) -> None:
    """Records a request at once (own commit), so the count survives restarts."""
    with connection:
        connection.execute(
            "INSERT INTO usage (at, city_id, calls, http_status, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            (utc_now(), city_id, calls, http_status, detail),
        )


def usage_24h(connection) -> float:
    """Calls spent in the last 24 hours."""
    since = (datetime.now(UTC) - timedelta(hours=24)).isoformat(timespec="seconds")
    total = connection.execute(
        "SELECT SUM(calls) FROM usage WHERE at >= ?", (since,)
    ).fetchone()[0]
    return total or 0


def wait_for_pause(connection, pause_minutes: float, log: Log) -> None:
    """Waits until `pause_minutes` have passed since the last recorded request (of any run)."""
    last = connection.execute("SELECT MAX(at) FROM usage").fetchone()[0]
    if last is None:
        return
    elapsed = (datetime.now(UTC) - datetime.fromisoformat(last)).total_seconds()
    remaining = pause_minutes * 60 - elapsed
    if remaining > 0:
        log(f"  Pause: waiting {remaining / 60:.1f} min since the last request")
        time.sleep(remaining)


def fetch_with_retries(
    connection,
    city_id: str,
    params: dict,
    cost: float,
    config: DownloadConfig,
    log: Log,
    get: Callable = requests.get,
) -> dict:
    """One API request with retries. Every response is recorded in `usage`.

    | Response                     | What happens |
    |------------------------------|--------------|
    | 200                          | record the cost and return the data |
    | 200 empty or unreadable      | record the cost (the API charges it), wait 65 s, retry |
    | 429 per minute               | wait 65 s and retry |
    | 429 per hour                 | wait 1 hour and retry |
    | 429 daily                    | raise DailyLimitReached: the batch stops |
    | 5xx or network error         | retry after 30 s, 60 s, 120 s |
    | other 4xx                    | raise DownloadError: retrying makes no sense |

    Error responses are recorded as 1 call, to be on the safe side. `get` is `requests.get`;
    tests pass a fake one.
    """
    retries = config.max_retries
    for attempt in range(1, retries + 1):
        try:
            response = get(ARCHIVE_URL, params=params, timeout=config.timeout_seconds)
        except requests.RequestException as error:
            wait = 30 * 2 ** (attempt - 1)
            log(
                f"  Network error ({type(error).__name__}). "
                f"Waiting {wait} s (attempt {attempt}/{retries})"
            )
            time.sleep(wait)
            continue

        if response.status_code == 200:
            record_usage(connection, city_id, cost, 200)
            try:
                return response.json()
            except ValueError:
                # Sometimes the server cuts the response and sends an empty 200
                wait = 65
                log(
                    f"  Empty or unreadable 200 response ({len(response.content)} bytes). "
                    f"Waiting {wait} s (attempt {attempt}/{retries})"
                )
                time.sleep(wait)
                continue

        try:
            reason = response.json().get("reason", response.text)
        except ValueError:
            reason = response.text
        reason = str(reason)[:200]
        record_usage(connection, city_id, 1, response.status_code, reason)

        if response.status_code == 429:
            if "Daily" in reason:
                raise DailyLimitReached(reason)
            wait = 3600 if "Hourly" in reason else 65
        elif response.status_code >= 500:
            wait = 30 * 2 ** (attempt - 1)
        else:
            raise DownloadError(f"HTTP {response.status_code}: {reason}")

        log(
            f"  HTTP {response.status_code} ({reason}). "
            f"Waiting {wait} s (attempt {attempt}/{retries})"
        )
        time.sleep(wait)

    raise DownloadError(f"No valid response after {retries} attempts")


def validate(payload: dict, start: str, end: str) -> list[str]:
    """Problems of a response (empty list if it is fine): exactly every day of the period,
    no empty values and always t_min ≤ t_mean ≤ t_max."""
    daily = payload.get("daily", {})
    expected = pd.date_range(start, end, freq="D").strftime("%Y-%m-%d").tolist()
    problems = []
    if daily.get("time") != expected:
        problems.append(
            f"dates: {len(daily.get('time', []))} received, {len(expected)} expected"
        )
    for variable in DAILY_VARIABLES:
        empty = sum(value is None for value in daily.get(variable, [None]))
        if empty:
            problems.append(f"{variable}: {empty} empty values")
    if not problems:
        inconsistent = sum(
            not (t_min <= t_mean <= t_max)
            for t_mean, t_max, t_min in zip(*(daily[v] for v in DAILY_VARIABLES))
        )
        if inconsistent:
            problems.append(
                f"{inconsistent} days with t_min > t_mean or t_mean > t_max"
            )
    return problems


def mark_error(connection, city_id: str, message: str) -> None:
    with connection:
        connection.execute(
            "UPDATE downloads SET status = 'error', last_error = ? WHERE city_id = ?",
            (message[:300], city_id),
        )


def download_city(
    connection,
    city_id: str,
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    config: DownloadConfig,
    log: Log,
    get: Callable = requests.get,
) -> bool:
    """Downloads, validates and saves one city in one transaction. True if it is complete."""
    with connection:
        connection.execute(
            "UPDATE downloads SET attempts = attempts + 1 WHERE city_id = ?", (city_id,)
        )

    cost = request_cost(days_between(start, end))
    payload = fetch_with_retries(
        connection,
        city_id,
        build_params(latitude, longitude, start, end),
        cost,
        config,
        log,
        get,
    )

    problems = validate(payload, start, end)
    if problems:
        mark_error(connection, city_id, "; ".join(problems))
        log(f"  ✗ Invalid data: {'; '.join(problems)}")
        return False

    daily = payload["daily"]
    rows = zip(repeat(city_id), daily["time"], *(daily[v] for v in DAILY_VARIABLES))
    with connection:  # all or nothing
        connection.execute("DELETE FROM daily WHERE city_id = ?", (city_id,))
        connection.executemany(
            "INSERT INTO daily (city_id, date, t_mean, t_max, t_min) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        connection.execute(
            "UPDATE cities SET era5_lat = ?, era5_lon = ?, era5_elevation = ? WHERE id = ?",
            (
                payload["latitude"],
                payload["longitude"],
                payload.get("elevation"),
                city_id,
            ),
        )
        connection.execute(
            """UPDATE downloads
               SET status = 'complete', last_error = NULL, start_date = ?, end_date = ?,
                   n_days = ?, downloaded_at = ?
               WHERE city_id = ?""",
            (start, end, len(daily["time"]), utc_now(), city_id),
        )

    # Another complete city with the same ERA5 cell would have the same data
    same_cell = [
        row[0]
        for row in connection.execute(
            """SELECT c.id FROM cities c JOIN downloads d ON d.city_id = c.id
               WHERE d.status = 'complete' AND c.id != ? AND c.era5_lat = ? AND c.era5_lon = ?""",
            (city_id, payload["latitude"], payload["longitude"]),
        )
    ]
    if same_cell:
        with connection:
            connection.execute(
                "UPDATE downloads SET warning = ? WHERE city_id = ?",
                (f"same ERA5 cell as {', '.join(same_cell)}", city_id),
            )
        log(f"  ⚠ Same ERA5 cell as {', '.join(same_cell)}")

    log(
        f"  ✓ {len(daily['time']):,} days saved "
        f"(cell {payload['latitude']}, {payload['longitude']})"
    )
    return True


def run_batch(
    connection,
    start: str,
    end: str,
    config: DownloadConfig,
    log: Log = print,
    db_name: str = "database",
    get: Callable = requests.get,
) -> int:
    """Downloads the cities that are not complete, by priority and order, while the budget
    allows it. Returns how many were completed.

    A city that fails is marked as `error` and retried in later batches, up to
    `max_attempts_per_city`. Unexpected errors are logged with their traceback and the batch
    goes on with the next city; the API daily limit ends the batch.
    """
    pending = connection.execute(
        """SELECT c.id, c.name, c.latitude, c.longitude
           FROM cities c JOIN downloads d ON d.city_id = c.id
           WHERE d.status != 'complete' AND d.attempts < ?
           ORDER BY c.priority, c.download_order""",
        (config.max_attempts_per_city,),
    ).fetchall()

    log(f"=== Batch in {db_name}: {len(pending)} pending cities ===")
    if not pending:
        log("No pending city left.")
        return 0

    cost = request_cost(days_between(start, end))
    completed = 0
    for number, (city_id, name, latitude, longitude) in enumerate(pending, start=1):
        spent = usage_24h(connection)
        if spent + cost > config.daily_budget:
            log(
                f"Budget: {spent:,.0f} calls in 24 h; the next one ({cost:.0f}) "
                f"does not fit in {config.daily_budget:,.0f}. End of batch."
            )
            break

        wait_for_pause(connection, config.pause_minutes, log)
        log(f"[{number}/{len(pending)}] {name} ({city_id}) · usage 24 h: {spent:,.0f}")
        try:
            if download_city(
                connection, city_id, latitude, longitude, start, end, config, log, get
            ):
                completed += 1
        except DailyLimitReached as error:
            log(
                f"API daily limit reached ({error}). End of batch; completed cities are saved."
            )
            break
        except DownloadError as error:
            mark_error(connection, city_id, str(error))
            log(f"  ✗ {error}")
        except KeyboardInterrupt:
            log("Batch stopped by hand (■). Completed cities are saved.")
            raise
        # On purpose: one city failing in an unexpected way must not stop the whole batch
        except Exception as error:  # noqa: BLE001
            summary = f"Unexpected error: {type(error).__name__}: {error}"
            log(f"  ✗ {summary}")
            log("  Traceback:\n" + traceback.format_exc())
            mark_error(connection, city_id, summary)

    log(f"=== End of batch: {completed} cities completed ===")
    return completed


def import_clima_mundial(connection, source: Path) -> int:
    """Copies the cities already downloaded by the clima-mundial project (its data/clima.db).

    Only cities that are in `cities` (same ids) and `complete` in the source are copied, with
    their ERA5 cell and download status. Cities already complete here are not touched.
    Returns how many cities were imported.
    """
    if not Path(source).exists():  # ATTACH would create an empty database
        raise FileNotFoundError(source)
    connection.execute("ATTACH DATABASE ? AS source", (str(source),))
    try:
        to_import = [
            row[0]
            for row in connection.execute(
                """SELECT d.id_ciudad FROM source.descargas d
                   JOIN cities c ON c.id = d.id_ciudad
                   JOIN downloads mine ON mine.city_id = c.id
                   WHERE d.estado = 'completa' AND mine.status != 'complete'"""
            )
        ]
        with connection:
            for city_id in to_import:
                connection.execute("DELETE FROM daily WHERE city_id = ?", (city_id,))
                connection.execute(
                    """INSERT INTO daily (city_id, date, t_mean, t_max, t_min)
                       SELECT id_ciudad, fecha, t_media, t_max, t_min
                       FROM source.diario WHERE id_ciudad = ?""",
                    (city_id,),
                )
                connection.execute(
                    """UPDATE cities SET (era5_lat, era5_lon, era5_elevation) =
                       (SELECT lat_era5, lon_era5, elevacion_era5 FROM source.ciudades
                        WHERE id = ?) WHERE id = ?""",
                    (city_id, city_id),
                )
                connection.execute(
                    """UPDATE downloads SET (status, last_error, start_date, end_date,
                                             n_days, downloaded_at) =
                       (SELECT 'complete', NULL, fecha_inicio, fecha_fin, n_dias,
                               descargada_en
                        FROM source.descargas WHERE id_ciudad = ?) WHERE city_id = ?""",
                    (city_id, city_id),
                )
    finally:
        connection.execute("DETACH DATABASE source")
    return len(to_import)


# Shared copy of the data: one compact Parquet file instead of the ~250 MB database
SHARED_COLUMNS = ["city_id", "date", *DAILY_VARIABLES.values()]
SHARED_CELL_COLUMNS = ["era5_lat", "era5_lon", "era5_elevation"]


def export_parquet(connection, path: Path) -> int:
    """Writes every complete city to a Parquet file, to share the data without the API.

    Each row is one day of one city, with the ERA5 cell of the city (repeated values cost
    almost nothing once compressed): about 23 MB for 140 cities. Returns how many cities.
    """
    data = pd.read_sql(
        """SELECT d.city_id, d.date, d.t_mean, d.t_max, d.t_min,
                  c.era5_lat, c.era5_lon, c.era5_elevation
           FROM daily d
           JOIN downloads x ON x.city_id = d.city_id
           JOIN cities c ON c.id = d.city_id
           WHERE x.status = 'complete'
           ORDER BY d.city_id, d.date""",
        connection,
    )
    data["city_id"] = data["city_id"].astype("category")
    data["date"] = pd.to_datetime(data["date"])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(path, index=False, compression="zstd")
    return data["city_id"].nunique()


def import_parquet(connection, path: Path) -> int:
    """Imports the cities of a file written by `export_parquet`.

    Only cities that are in `cities` and not complete yet are imported, each one validated
    like a download (every day of its period, no empty values, t_min ≤ t_mean ≤ t_max) and
    saved in one transaction. Running it again does nothing. Returns how many were imported.
    """
    data = pd.read_parquet(path)
    known = {row[0] for row in connection.execute("SELECT id FROM cities")}
    complete = {
        row[0]
        for row in connection.execute(
            "SELECT city_id FROM downloads WHERE status = 'complete'"
        )
    }
    imported = 0
    for city_id, rows in data.groupby("city_id", observed=True):
        if city_id not in known or city_id in complete:
            continue
        rows = rows.sort_values("date")
        dates = rows["date"].dt.strftime("%Y-%m-%d").tolist()
        values = rows[list(DAILY_VARIABLES.values())]
        if values.isna().any().any():
            raise ValueError(f"{city_id}: empty values in {path}")
        payload = {
            "daily": {
                "time": dates,
                **{
                    api: values[column].tolist()
                    for api, column in DAILY_VARIABLES.items()
                },
            }
        }
        problems = validate(payload, dates[0], dates[-1])
        if problems:
            raise ValueError(f"{city_id}: {'; '.join(problems)}")

        cell = rows[SHARED_CELL_COLUMNS].iloc[0].tolist()
        with connection:  # all or nothing
            connection.execute("DELETE FROM daily WHERE city_id = ?", (city_id,))
            connection.executemany(
                "INSERT INTO daily (city_id, date, t_mean, t_max, t_min) "
                "VALUES (?, ?, ?, ?, ?)",
                zip(repeat(city_id), dates, *(values[c].tolist() for c in values)),
            )
            connection.execute(
                "UPDATE cities SET era5_lat = ?, era5_lon = ?, era5_elevation = ? "
                "WHERE id = ?",
                (*cell, city_id),
            )
            connection.execute(
                """UPDATE downloads
                   SET status = 'complete', last_error = NULL, start_date = ?,
                       end_date = ?, n_days = ?, downloaded_at = ?
                   WHERE city_id = ?""",
                (dates[0], dates[-1], len(dates), utc_now(), city_id),
            )
        imported += 1
    return imported
