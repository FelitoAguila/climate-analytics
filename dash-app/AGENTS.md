# AGENTS.md

## Project

`dash-app` is the **web app for climate-analytics**: a Plotly Dash application for
exploring the historical temperature of 140 cities, every day from 1940 to 2026. The data
comes from the Open-Meteo historical API (ERA5 reanalysis) and lives in a **Neon PostgreSQL**
database. The app only reads it.

The project started as a reusable, content-agnostic Dash template styled after the
**Materials Project** website (materialsproject.org). That shell is kept: the MP look, layout,
navigation, components, routing and theme are the foundation. Unlike the original template,
this app is now **climate-specific** — replace generic placeholder content when implementing
features.

This directory is a **standalone uv project** with its own `pyproject.toml`, `uv.lock`,
`.venv` and `.env`. It currently lives inside the `climate-analytics` monorepo, whose root is
a uv workspace, but `dash-app` is **not** a workspace member and must be managed on its
own. Always run its commands from this directory. The monorepo is being reorganised into
independent components, each with its own uv environment, so do not depend on the root
workspace, root `.venv`, or sibling packages.

## Environment and secrets

- **Never read `dash-app/.env`.** It stores the database password. Read and write
  `.env.example` instead; it is the safe, committed representation of `.env`.
- `.env` is git-ignored. Never commit it, print it, log its contents, or echo the connection
  string. Connection errors must not include the URL or password.
- The app must use a **read-only** Neon role. Never use the loader/admin credentials here.
- Settings use `pydantic-settings`: environment variables take precedence over the explicit
  `dash-app/.env` file. Do not rely on the current working directory.
- Missing or invalid configuration fails at startup (`create_app()` calls `get_settings()`).
  Runtime database outages still surface as `DataUnavailable`.
- Local setup: `cp .env.example .env`, then paste the read-only connection string.
- Production (Render): set secrets in the platform environment, set `DASH_DEBUG=false`, and
  never upload `.env`.

| Variable | Purpose |
| --- | --- |
| `READONLY_DATABASE_URL` | Read-only Neon connection string (required) |
| `HOST` | Bind address (default `0.0.0.0`) |
| `PORT` | Port (default `8050`) |
| `DASH_DEBUG` | Dash debug mode (default `false`) |
| `DB_POOL_SIZE` | Pool size (default `5`) |
| `DB_MAX_OVERFLOW` | Extra pooled connections (default `5`) |
| `DB_POOL_RECYCLE_SECONDS` | Connection recycle age (default `300`) |
| `DB_POOL_TIMEOUT_SECONDS` | Pool wait timeout (default `10`) |
| `DB_CONNECT_TIMEOUT_SECONDS` | Neon connect timeout (default `10`) |
| `DB_STATEMENT_TIMEOUT_MS` | Statement timeout (default `15000`) |

## Data source and schema

The app consumes the `public` schema of the Neon database. Two tables exist today; more can
be added later.

| Table | One row per | Key columns |
| --- | --- | --- |
| `cities` | city | `id` (text PK), `name`, `country`, `country_code`, `continent`, `latitude`, `longitude`, `cell_lat`, `cell_lon`, `population`, `is_capital`, `latitude_band`, `coast_distance_km`, `coastal`, `priority`, `download_order`, `era5_lat`, `era5_lon`, `era5_elevation` |
| `daily` | city and day | `city_id` (FK → `cities.id`), `date` (DATE), `t_mean`, `t_max`, `t_min` (REAL, °C); PK `(city_id, date)` |

Facts to keep in mind:

- 140 cities, roughly 4.4 million daily rows, 1940–2026.
- Each city is one ERA5 grid cell (~25 km), not a weather station; the urban heat island is
  not captured.
- ERA5 data arrives about a week late. The database never reaches today.
- The monorepo's Airflow DAG updates the database daily. This app is strictly read-only.
- Data quality checks used elsewhere: `t_min <= t_mean <= t_max`, no missing days per city,
  and each city's latest date is not stale. Use these for the data-status feature.

Query guidance:

- **Aggregate in SQL**; never pull all of `daily` into memory. Query only the cities, dates
  and columns a page needs.
- Filter by `city_id` and/or `date` so the `daily` primary key is used.
- Always use parameterised queries; never interpolate user input into SQL.
- Query per need, with the `data.db.ttl_cache` cache for expensive aggregates. Do not
  preload the full dataset at startup.
- Shape results with pandas, but keep large work in PostgreSQL.
- Tests must not require Neon or the network: mock/fixture the data layer.

## Data layer

The read-only data layer is implemented under `src/dash_app/data/`; see
`src/dash_app/data/README.md` for the full reference. In short:

- `settings.py` defines a frozen `Settings` model with `pydantic-settings`, validates
  `READONLY_DATABASE_URL` as a `SecretStr`, and provides `get_settings()` and
  `database_url()` (normalised to `postgresql+psycopg://`).
- `data/db.py` owns the lazy SQLAlchemy engine, connection pool, `fetch_df()`, the
  `cachetools` TTL cache and SQL error wrapping.
- `data/queries.py` owns all SQL and DataFrame shaping.
- `data/__init__.py` is the public API; pages and callbacks import from `dash_app.data`.
- Sessions are read-only (`default_transaction_read_only=on`), with a configurable
  statement timeout (default 15 s).
- Exceptions: `ConfigurationError` and `DataUnavailable`, both under `DataLayerError`.
  Pages should catch `DataUnavailable` and show a notification.
- Cached functions return DataFrame copies. Use `clear_data_caches()` after a refresh or
  in tests.

Public query API:

| Function | Purpose |
| --- | --- |
| `list_cities()` | All city metadata in download order |
| `get_city(city_id)` | One city or `None` |
| `city_daily(city_id, start=None, end=None)` | Daily temperatures |
| `city_annual_stats(city_id)` | Annual means, percentiles and anomalies |
| `city_summaries()` | Per-city warming metrics |
| `data_status()` | Coverage and freshness (`DatasetStatus`) |

## Current state

- The MP-style shell is implemented and tested (`uv run pytest`).
- The read-only data layer is implemented and tested offline (SQLAlchemy + psycopg3,
  cachetools, lazy engine, query API, error wrapping).
- Generic template pages still exist: home, features dashboard, browse list, detail, about
  and 404. Browse/detail still read `data/placeholder.py`; migrate them to the data API next.
- Branding, navigation and copy are still template placeholders.

## Architecture

```
dash-app/
├── pyproject.toml           # standalone project; own dependencies and entrypoint
├── uv.lock
├── .env / .env.example      # secrets (never read .env)
├── src/dash_app/
│   ├── __init__.py          # main() -> lazy import of app.main
│   ├── __main__.py          # python -m dash_app
│   ├── app.py               # create_app(): Dash instance, external CSS, layout, callbacks, run()
│   ├── settings.py          # pydantic-settings model + read-only URL normalisation
│   ├── errors.py            # DataLayerError, ConfigurationError, DataUnavailable
│   ├── config.py            # APP_* branding, theme tokens, NAV_LINKS, ABOUT_MENU, DASHBOARD_NAV, FOOTER_LINKS
│   ├── utils.py             # is_active(href, path) helper
│   ├── components/
│   │   ├── bulma.py         # Bulma primitives: container, columns/column, card*, hero, notification, level...
│   │   ├── shell.py         # full-page shell: navbar + content + footer + dcc.Location/stores
│   │   ├── navbar.py        # dark navy bar: brand/logo, links, About dropdown, theme toggle, burger
│   │   ├── sidenav.py       # collapsible icon sidebar (hover/focus expand + tap toggle)
│   │   ├── page_header.py   # breadcrumb + icon/title/action row
│   │   ├── footer.py
│   │   ├── search.py        # hero_banner() (hero section without search bar)
│   │   └── cards.py         # stat_card, feature_card, dashboard_card, content_card, stat_grid
│   ├── pages/
│   │   ├── registry.py      # path -> (title, nav_key, layout); dynamic-route matching
│   │   ├── home.py          # hero + stat cards + feature card grid + sample Plotly chart
│   │   ├── features.py      # /features: dashboard (sidebar + page header + card grid)
│   │   ├── list.py          # generic filterable/sortable table (browse)
│   │   ├── detail.py        # generic detail page, reads id from path
│   │   ├── about.py         # markdown overview
│   │   └── not_found.py     # 404
│   ├── callbacks/
│   │   ├── __init__.py      # register_callbacks(app)
│   │   ├── navigation.py    # pathname -> render page; mobile menu; document title
│   │   ├── search.py        # browse table filtering; prefill
│   │   ├── sidenav.py       # sidebar expand/collapse toggle (clientside)
│   │   └── theme.py         # light/dark toggle with dcc.Store persistence (clientside)
│   ├── data/
│   │   ├── __init__.py      # public read-only data API
│   │   ├── db.py            # lazy engine, fetch_df(), TTL cache, error wrapping
│   │   ├── queries.py       # SQL + DataFrame shaping
│   │   ├── README.md        # data-layer reference
│   │   └── placeholder.py   # neutral dummy rows; remove after pages migrate
│   └── assets/
│       ├── theme.css        # MP-inspired overrides + dark theme
│       └── logo.svg
└── tests/
    ├── test_navigation.py   # registry, filters, active-link, app bootstrap, index smoke test
    └── test_data.py         # offline data-layer tests
```

Keep data access isolated from pages: add SQL to `data/queries.py`, shape DataFrames there,
and have pages/callbacks call the public functions from `dash_app.data`. Do not scatter SQL
across layout or callback modules.

**Import boundary:** keep this app self-contained. Do not import the monorepo's `analysis`,
`pipelines`, or other sibling packages. If shared code is needed later, it must be added to
this project's `pyproject.toml` as an explicit dependency (and discussed first).

## Look & feel (do not regress)

The Materials Project look is the whole reason this project started from the template.

- **Bulma 0.9.4**, not Bootstrap:
  `https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.4/css/bulma.min.css`
- **Font Awesome 6.4.2**:
  `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css`
- **Primary color**: `hsl(171, 100%, 41%)` → teal `#00d1b2` (Bulma's default primary).
- Dark navy (`#202536`) sticky top navbar: logo left, links right (Features, About dropdown,
  theme toggle), mobile burger.
- No global sidebar in the shell — navigation lives in the navbar.
- Large centered hero on the home page (no search bar).
- `/features`: dashboard layout — collapsible icon sidebar (hover/focus expand), white page
  header (breadcrumbs + icon/title/Documentation button) and a responsive card grid on
  `#F3F3F3`.
- Card grid + KPI/stat cards, chips/tags, notifications, breadcrumbs, MP-style tables.
- Footer with links, copyright and licensing line.
- Responsive Bulma `columns` / `is-*` classes.
- Light/dark theme via `html[data-theme]` attribute + CSS variables.
- Prefer the `components/bulma.py` helpers over raw Bulma class strings.
- **Do not depend on** `crystal_toolkit`, `dash-mp-components`, `mp-react-components`, or
  materials-science packages. Use them only as visual reference.

## Routing and callbacks already delivered

Routing mirrors MP: manual `dcc.Location` + callbacks, not Dash Pages. Dynamic
`/<section>/<id>` routes are supported.

1. Route rendering (`dcc.Location.pathname` → page content), incl. 404 fallback.
2. Mobile menu burger toggle (off-canvas navbar drawer).
3. Document title sync + `#features` smooth-scroll anchor (clientside).
4. Browse table filtering (text/category/status/sort) + prefill.
5. Light/dark theme toggle with `dcc.Store`/localStorage persistence (clientside).
6. Features sidebar expand/collapse toggle (clientside; hover/focus handled in CSS).

## Decisions

| Topic | Decision |
| --- | --- |
| Purpose | Climate-analytics web app built on the MP-style Dash template |
| Visual style | Bulma + custom `theme.css` (authentic MP look), Font Awesome icons |
| Routing | Manual `dcc.Location` + callbacks; dynamic `/<section>/<id>` |
| Data source | Neon PostgreSQL, `public.cities` and `public.daily`, read-only |
| Credentials | `READONLY_DATABASE_URL` from the environment or `dash-app/.env`; never use writer credentials |
| Data access | Query per need + small cache; no full preload at startup; aggregate in SQL |
| DB client | SQLAlchemy Core + psycopg3 (SQLAlchemy owns the pool; psycopg is the driver) |
| Caching | `cachetools.TTLCache`, thread-safe, bounded; cached DataFrames are copied |
| Configuration | `pydantic-settings` model, validated at startup, URL stored as `SecretStr` |
| Errors | `DataLayerError` → `ConfigurationError` / `DataUnavailable`; UI shows a notification |
| Coupling | Self-contained app; no imports from sibling monorepo packages |
| Environment | Standalone uv project with its own `.venv`; not part of the root workspace |
| Do NOT use | `crystal_toolkit`, `dash-mp-components`, `mp-react-components` |

## Conventions

- Content may now be climate-specific; keep the shell and components reusable where easy.
- Config-driven: nav items in `config.NAV_LINKS` / `config.ABOUT_MENU` /
  `config.DASHBOARD_NAV`; pages in `pages/registry.py`.
- Keep SQL in `data/queries.py`, parameterised, and scoped to what the page needs.
- Use `fetch_df()`; do not create ad-hoc engines or connections outside `data/db.py`.
- Decorate expensive queries with `@ttl_cache(...)` and keep TTLs in `queries.py`.
- Treat the database as read-only. Never add write/update/delete statements.
- Do not expose connection strings or raw database errors to the UI.
- No comments in code unless necessary.
- Do not add materials-science dependencies.
- Tests must stay offline and must not require a live Neon connection.
- `.env` is never read by agents; use `.env.example` for documentation.

## Commands

Run from `dash-app/`:

- Install / sync deps: `uv sync`
- Run app: `uv run dash-app` (or `uv run python -m dash_app`)
- Tests: `uv run pytest`
- Lint/format: not configured yet (the monorepo root uses ruff; add it here if introduced)

## Roadmap

Completed from the template:

- [x] MP-style shell, components, routing, callbacks, theme and placeholder pages.
- [x] Tests for registry, filters, active links, app bootstrap and index rendering.

Next, in rough order:

- [x] Choose and add the DB client (SQLAlchemy Core + psycopg3).
- [x] Implement the read-only `data/` layer using `READONLY_DATABASE_URL`.
- [x] Add TTL caching for expensive aggregates.
- [x] Harden configuration with pydantic-settings and fail-fast validation.
- [ ] Replace `data/placeholder.py` usage with real queries for the pages that need data.
- [ ] Plan the climate feature set in detail with the user. Directions already identified:
      global maps and rankings, and database freshness/status. Per-city browse/detail,
      warming trends, distributions (bells) and city comparison may follow; specifics are
      still to be defined.
- [ ] Update branding, navigation, copy and the README for climate-analytics.
- [ ] Optional: configure ruff (lint/format) and add it to dev dependencies.
