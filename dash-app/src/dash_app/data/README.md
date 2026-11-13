# Data layer

Read-only access to the climate database for the Dash app. The app consumes the Neon
PostgreSQL tables `public.cities` and `public.daily`; it never writes to them.

## Files

```
src/dash_app/
├── settings.py        # typed settings (pydantic-settings) + URL normalisation
└── data/
    ├── __init__.py    # public API re-exports
    ├── db.py          # engine, query execution, cache, SQL error wrapping
    ├── queries.py     # SQL and DataFrame shaping
    └── placeholder.py # temporary data used by the template pages
```

The UI imports from `dash_app.data`, not from `db.py` or `queries.py` directly.

## Configuration

`settings.py` defines a typed `Settings` model with **pydantic-settings**. It loads
`dash-app/.env` explicitly for local development, and environment variables take precedence
over the file. The only required variable is:

```dotenv
READONLY_DATABASE_URL=postgresql://climate_reader:password@host/dbname?sslmode=require
```

Runtime settings:

| Variable | Default | Purpose |
| --- | --- | --- |
| `READONLY_DATABASE_URL` | — | Read-only Neon URL (required) |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8050` | Port |
| `DASH_DEBUG` | `false` | Dash debug mode |
| `DB_POOL_SIZE` | `5` | SQLAlchemy pool size |
| `DB_MAX_OVERFLOW` | `5` | Extra connections above the pool size |
| `DB_POOL_RECYCLE_SECONDS` | `300` | Recycle connections after this age |
| `DB_POOL_TIMEOUT_SECONDS` | `10` | Wait for a pooled connection |
| `DB_CONNECT_TIMEOUT_SECONDS` | `10` | Neon connection timeout |
| `DB_STATEMENT_TIMEOUT_MS` | `15000` | PostgreSQL statement timeout |

Rules:

- Use a **read-only** Neon role.
- Never commit `.env` or print its contents. Use `.env.example` for documentation.
- The URL is validated and converted internally to SQLAlchemy's psycopg3 driver
  (`postgresql+psycopg://`).
- The URL is stored as a `SecretStr`, so it is masked in reprs and validation errors.
- Configuration is validated when the app is created. Missing or invalid settings stop
  startup with a clear `ValidationError`.
- The database engine itself is still lazy: a temporary outage after startup raises
  `DataUnavailable`, which pages can render as a notification.

The engine is configured with connection pooling and pre-ping (Neon may suspend
connections), a read-only session (`default_transaction_read_only=on`), the configured
statement timeout, and `application_name=dash-app`.

### Production

Do not ship `.env` to the hosting platform. On Render, set `READONLY_DATABASE_URL` in the
Environment tab as a secret, set `DASH_DEBUG=false`, and let Render provide `PORT`. The same
environment variables work on any platform that follows the 12-factor pattern.

## Public API

```python
from dash_app.data import (
    city_annual_stats,
    city_daily,
    city_summaries,
    data_status,
    get_city,
    list_cities,
)
```

| Function | Returns |
| --- | --- |
| `list_cities()` | All cities, ordered by `download_order` |
| `get_city(city_id)` | One city as a `dict`, or `None` |
| `city_daily(city_id, start=None, end=None)` | Daily `t_mean`, `t_max`, `t_min` |
| `city_annual_stats(city_id)` | Annual means, percentiles and anomalies |
| `city_summaries()` | One row per city with warming metrics |
| `data_status()` | `DatasetStatus` with coverage and freshness |

`city_daily` defaults to the full series, so use a date range when a page needs only part
of it.

### Columns and types

- `date` columns are pandas `datetime64`.
- Temperatures are `float`.
- `is_capital` and `coastal` are `bool`.
- `city_id` and city `id` are strings.
- List functions return an empty DataFrame with stable columns when there is no data.
- `get_city` returns `None` for an unknown identifier.

### Annual statistics

`city_annual_stats` returns one row per year:

| Column | Meaning |
| --- | --- |
| `year`, `days` | Year and number of daily rows |
| `mean` | Annual mean of `t_mean` |
| `p05`, `p25`, `p50`, `p75`, `p95` | Percentiles of `t_mean` |
| `max_mean` | Annual mean of the daily maxima |
| `min_mean` | Annual mean of the daily minima |
| `anomaly` | `mean` minus the 1961–1990 reference mean |

`city_summaries` uses complete years only (365/366 days) and adds:

`first_year`, `last_year`, `reference_mean`, `recent_mean`, `difference`,
`trend_decade`, `recent_trend`, `warmest_year`.

Domain constants live at the top of `queries.py`:

```python
REFERENCE_PERIOD = (1961, 1990)
RECENT_YEARS = 10
RECENT_TREND_FROM = 1975
LESS_RELIABLE_BEFORE = 1950
```

### Data status

`data_status()` returns a `DatasetStatus`:

```python
@dataclass(frozen=True)
class DatasetStatus:
    city_count: int
    row_count: int
    first_date: date | None
    latest_date: date | None
    cities: pd.DataFrame
```

The `cities` frame has one row per city with `first_date`, `last_date`, `days`,
`expected_days`, `missing_days`, `days_behind` and `complete`. Gaps are detected with
`MAX(date) - MIN(date) + 1 <> COUNT(*)`.

## SQL rules

- Aggregate in PostgreSQL; do not load all of `daily` into memory.
- Filter by `city_id` and/or `date` so the `daily` primary key is used.
- Always use named parameters (`:city_id`); never interpolate user input.
- Keep derived metrics that only need small result sets in pandas.
- Keep SQL in `queries.py`; pages and callbacks should not contain SQL.

## Caching

Expensive results are cached with `cachetools.TTLCache` through `data.db.ttl_cache`:

| Data | TTL |
| --- | --- |
| Cities | 1 hour |
| Daily series per city | 10 minutes |
| Annual statistics and summaries | 30 minutes |
| Data status | 5 minutes |

The cache is thread-safe and bounded. Functions return copies of cached DataFrames, so
callers can sort or modify their results safely. Use `clear_data_caches()` after a data
refresh or in tests.

## Errors

Configuration problems are caught at startup by pydantic-settings and raise a
`ValidationError`; the app does not start with a missing or invalid URL.

Runtime data errors inherit from `DataLayerError`:

- `ConfigurationError`: a defensive fallback for an invalid SQLAlchemy URL.
- `DataUnavailable`: the database could not be reached or the query failed.

`DataUnavailable` has a safe message for the UI; the underlying SQLAlchemy or pandas error
is kept as the exception cause and is not shown to users. Pages should catch
`DataUnavailable` and render a notification instead of failing the callback.

## Tests

```bash
uv run pytest tests/test_data.py tests/test_settings.py
```

The tests are offline: they mock `fetch_df` and the engine, use `Settings(_env_file=None, ...)`
instead of the real `.env`, and never connect to Neon. `tests/conftest.py` supplies a harmless
dummy URL so `create_app()` can run without production configuration. Keep new data-layer
tests that way. If a live integration test is added, mark it and skip it by default.

## Adding a query

1. Add the SQL and a public function in `queries.py`.
2. Use `fetch_df(sql, params, parse_dates=...)`.
3. Shape and validate the DataFrame in a small `_prepare_*` helper.
4. Decorate with `@ttl_cache(seconds, maxsize=...)` if the result is expensive.
5. Export it from `data/__init__.py` if pages should use it.
6. Add an offline test with a mocked `fetch_df`.
