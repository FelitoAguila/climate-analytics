"""Loads the shared data into Neon (PostgreSQL in the cloud), for the web app to query.

Run it from the project root: `uv run load-neon` (`--limit N` loads only the first N cities).

- **Source:** `data/cities.csv` and `data/climate.parquet`, validated like a download.
- **Connection:** `DATABASE_URL` in the `.env` file (see `.env.example`). It holds the password,
  so it is never printed.
- **Resumable:** each city goes in one transaction, so it is either complete or absent, and
  running it again skips the cities already loaded.

| Table    | One row per | Contents |
|---|---|---|
| `cities` | city        | columns of data/cities.csv + the ERA5 cell returned by the API |
| `daily`  | city and day | temperatures; its primary key makes asking for one city fast |
"""

import argparse
import os
import time
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

from pipelines.download import (
    CITY_COLUMNS,
    DAILY_VARIABLES,
    SHARED_CELL_COLUMNS,
    check_shared_city,
    read_cities_csv,
)

CITIES_CSV = Path("data/cities.csv")
SHARED_PARQUET = Path("data/climate.parquet")
ENV_FILE = Path(".env")
EXAMPLE_URL = "postgresql://user:password@host/dbname?sslmode=require"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cities (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    country           TEXT,
    country_code      TEXT,
    continent         TEXT,
    latitude          DOUBLE PRECISION NOT NULL,
    longitude         DOUBLE PRECISION NOT NULL,
    cell_lat          DOUBLE PRECISION,
    cell_lon          DOUBLE PRECISION,
    population        INTEGER,
    is_capital        INTEGER,
    latitude_band     TEXT,
    coast_distance_km INTEGER,
    coastal           INTEGER,
    priority          INTEGER,
    download_order    INTEGER,
    era5_lat          DOUBLE PRECISION,  -- cell returned by the API
    era5_lon          DOUBLE PRECISION,
    era5_elevation    DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS daily (
    city_id TEXT NOT NULL REFERENCES cities(id),
    date    DATE NOT NULL,
    t_mean  REAL NOT NULL,  -- 4 bytes: enough for values with one decimal
    t_max   REAL NOT NULL,
    t_min   REAL NOT NULL,
    PRIMARY KEY (city_id, date)
);
"""


def database_url() -> str:
    """The connection string of the `.env` file, or an error that says what to do."""
    load_dotenv(ENV_FILE)
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url or url == EXAMPLE_URL:
        raise SystemExit(
            "DATABASE_URL is not set. Copy .env.example to .env and paste your Neon "
            "connection string (direct, without -pooler)."
        )
    return url


def connect(url: str) -> psycopg.Connection:
    """Opens the connection. The cause of a failure is hidden because it can show the URL."""
    try:
        return psycopg.connect(url, autocommit=True)
    except psycopg.Error as error:
        raise SystemExit(
            f"Could not connect to the database ({type(error).__name__}). "
            "Check DATABASE_URL in .env."
        ) from None


def read_shared_data(path: Path) -> dict[str, pd.DataFrame]:
    """The rows of each city of a file written by `export_parquet`, by city id."""
    if not Path(path).exists():
        raise SystemExit(
            f"{path} does not exist. Download the shared copy (see the README) or write it "
            "with section 7 of notebooks/03_download.ipynb."
        )
    data = pd.read_parquet(path)
    return {
        str(city_id): rows for city_id, rows in data.groupby("city_id", observed=True)
    }


def city_row(city: pd.Series, rows: pd.DataFrame) -> list:
    """Values of one city for the `cities` table, in the order of `CITY_INSERT`."""
    return [*city[list(CITY_COLUMNS)].astype(object).tolist()] + [
        rows[column].iloc[0].item() for column in SHARED_CELL_COLUMNS
    ]


def daily_rows(city_id: str, rows: pd.DataFrame) -> list[tuple]:
    """Rows of one city for the `daily` table, with real dates."""
    columns = (rows[column].tolist() for column in DAILY_VARIABLES.values())
    return [
        (city_id, day, *temperatures)
        for day, *temperatures in zip(rows["date"].dt.date, *columns, strict=True)
    ]


_CITY_TABLE_COLUMNS = [*CITY_COLUMNS.values(), *SHARED_CELL_COLUMNS]
CITY_INSERT = (
    f"INSERT INTO cities ({', '.join(_CITY_TABLE_COLUMNS)}) "
    f"VALUES ({', '.join(['%s'] * len(_CITY_TABLE_COLUMNS))}) "
    "ON CONFLICT (id) DO UPDATE SET "
    + ", ".join(f"{c} = EXCLUDED.{c}" for c in _CITY_TABLE_COLUMNS if c != "id")
)
DAILY_COPY = (
    f"COPY daily (city_id, date, {', '.join(DAILY_VARIABLES.values())}) FROM STDIN"
)


def load_city(connection, city: pd.Series, city_id: str, rows: pd.DataFrame) -> None:
    """Writes one city, all or nothing, replacing what it had."""
    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute(CITY_INSERT, city_row(city, rows))
        cursor.execute("DELETE FROM daily WHERE city_id = %s", (city_id,))
        with cursor.copy(DAILY_COPY) as copy:
            for row in daily_rows(city_id, rows):
                copy.write_row(row)


def cities_to_load(
    city_ids: list[str], shared: dict[str, pd.DataFrame], loaded: dict[str, int]
) -> list[str]:
    """Cities of the list that are in the file and do not have all their days in the database."""
    return [
        city_id
        for city_id in city_ids
        if city_id in shared and loaded.get(city_id) != len(shared[city_id])
    ]


def load(connection, cities: pd.DataFrame, shared: dict, log=print) -> int:
    """Creates the tables and loads the missing cities. Returns how many were loaded."""
    connection.execute(SCHEMA)
    loaded = dict(
        connection.execute(
            "SELECT city_id, COUNT(*) FROM daily GROUP BY city_id"
        ).fetchall()
    )
    pending = cities_to_load(list(cities["id"]), shared, loaded)
    log(f"{len(cities)} cities requested, {len(pending)} to load")

    by_id = cities.set_index("id", drop=False)
    for position, city_id in enumerate(pending, start=1):
        rows = check_shared_city(city_id, shared[city_id], SHARED_PARQUET)
        started = time.monotonic()
        load_city(connection, by_id.loc[city_id], city_id, rows)
        log(
            f"[{position}/{len(pending)}] {city_id}: {len(rows):,} days "
            f"in {time.monotonic() - started:.1f} s"
        )
    return len(pending)


def summary(connection) -> str:
    """Cities, rows and space used in the database."""
    cities, rows = connection.execute(
        "SELECT COUNT(DISTINCT city_id), COUNT(*) FROM daily"
    ).fetchone()
    size = connection.execute(
        "SELECT pg_size_pretty(pg_total_relation_size('cities') "
        "+ pg_total_relation_size('daily'))"
    ).fetchone()[0]
    return f"In the database: {cities} cities, {rows:,} rows, {size}"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Loads the shared data into Neon.")
    parser.add_argument(
        "--limit", type=int, help="load only the first N cities (to test)"
    )
    args = parser.parse_args(argv)

    url = database_url()
    cities = read_cities_csv(CITIES_CSV).head(args.limit)
    shared = read_shared_data(SHARED_PARQUET)
    with connect(url) as connection:
        load(connection, cities, shared)
        print(summary(connection))
