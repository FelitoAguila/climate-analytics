# dash-app

The [Plotly Dash](https://dash.plotly.com/) web app for **climate-analytics**: explore the
historical temperature of 140 cities, every day from 1940 onwards. The data lives in a
read-only Neon PostgreSQL database and comes from the Open-Meteo historical API (ERA5
reanalysis).

The visual design is inspired by the [Materials Project](https://materialsproject.org)
website and keeps the template shell: top navbar, hero section, cards, tables, tags,
breadcrumbs, footer and a light/dark theme.

## Features

- Materials Project inspired layout built on **Bulma** + **Font Awesome**.
- Manual `dcc.Location` routing with callbacks (supports dynamic `/<section>/<id>`).
- Reusable, dependency-light Bulma helpers (`components/bulma.py`).
- Read-only data layer for Neon: SQL queries, pandas results, TTL caching and safe errors.
- Data Explorer at `/explorer`: table documentation, column reference and bounded record
  previews for `cities` and `daily`.
- Pages: dashboard, features, data explorer, about and a 404.
- Navbar navigation (Features link + About dropdown), mobile menu, and a `/features`
  dashboard with a collapsible icon sidebar, page header and feature card grid.
- Light/dark theme with `localStorage` persistence.

## Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)

## Quickstart

```bash
uv sync
cp .env.example .env   # then paste the read-only Neon connection string
uv run dash-app        # or: uv run python -m dash_app
```

Then open <http://localhost:8050>.

Environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `READONLY_DATABASE_URL` | — | Read-only Neon connection string (required) |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8050` | Port |
| `DASH_DEBUG` | `false` | Enable Dash debug mode |
| `DB_POOL_SIZE` | `5` | SQLAlchemy pool size |
| `DB_MAX_OVERFLOW` | `5` | Extra connections above the pool size |
| `DB_POOL_RECYCLE_SECONDS` | `300` | Recycle connections after this age |
| `DB_POOL_TIMEOUT_SECONDS` | `10` | Wait for a pooled connection |
| `DB_CONNECT_TIMEOUT_SECONDS` | `10` | Neon connection timeout |
| `DB_STATEMENT_TIMEOUT_MS` | `15000` | PostgreSQL statement timeout |

`.env` holds the database password. It is git-ignored; never commit or share it. Use
`.env.example` as the safe reference. Configuration is validated at startup: a missing or
invalid URL stops the app with a clear error.

## Deploying to Render

The repository includes a root [`render.yaml`](../render.yaml) Blueprint that points Render
at the `dash-app` directory. The app is served by Gunicorn through `dash_app.app:server`.

### Before deploying

1. Merge the dashboard branch into `main`.
2. Confirm `uv run pytest` and `uv run ruff check src tests` pass from `dash-app/`.
3. Create or reuse a **read-only** Neon role.
4. Copy the pooled Neon connection string for the app. If you hit prepared-statement
   errors through the pooler, use the direct URL instead (without `-pooler`).

### Option A: Render Blueprint

1. Push the repository to GitHub with `render.yaml` at the root.
2. In Render, choose **New → Blueprint**.
3. Select the repository and the `main` branch.
4. When prompted, set `READONLY_DATABASE_URL` to the secret Neon URL.
5. Apply the Blueprint.

Render reads `rootDir: dash-app`, so `pyproject.toml`, `uv.lock` and `.python-version`
come from the dashboard project.

### Option B: Manual Web Service

| Setting | Value |
| --- | --- |
| Language | Python 3 |
| Root Directory | `dash-app` |
| Build Command | `uv sync --frozen --no-dev` |
| Start Command | `uv run --frozen --no-dev gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 --access-logfile - dash_app.app:server` |
| Health Check Path | `/healthz` |
| Plan | Free |

Environment variables:

| Variable | Value |
| --- | --- |
| `READONLY_DATABASE_URL` | Secret pooled Neon URL |
| `DASH_DEBUG` | `false` |
| `UV_VERSION` | `0.13.6` |

Do not upload `.env`. Render provides `PORT`; Gunicorn binds to `0.0.0.0:$PORT`.
`HOST` and `PORT` from `settings.py` are only used by the local `uv run dash-app` command.

### After deploying

- Open `/` and confirm the Overview cards show live data.
- Confirm `/healthz` returns `200` with `{"status": "ok"}`.
- Check the theme toggle, `/about` and `/features`.
- Review Render logs for startup errors, database errors or worker restarts.

### Notes and troubleshooting

- The free tier sleeps after inactivity, so the first request can be slow. Neon may also
  cold-start.
- Keep the pool small; the defaults (`DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=5`) are fine for one
  Render instance.
- The app validates settings at startup. A missing or invalid `READONLY_DATABASE_URL` stops
  the worker with a clear validation error.
- If Render reports “no open ports detected”, verify the start command binds
  `0.0.0.0:$PORT`.
- If the build cannot find `uv.lock`, set the Root Directory to `dash-app`.
- If the pooled Neon URL produces intermittent prepared-statement errors, switch to the
  direct Neon URL or disable prepared statements in the driver.

## Project layout

```
src/dash_app/
├── app.py            # create_app() factory + entry point
├── settings.py       # explicit .env loading + database URL handling
├── errors.py         # DataLayerError, ConfigurationError, DataUnavailable
├── config.py         # branding, theme tokens, navigation
├── utils.py          # is_active() helper
├── components/       # shell, navbar, sidenav, page header, footer, search, cards, tables, Bulma helpers
├── pages/            # page layouts (incl. explorer) + registry
├── callbacks/        # navigation, sidenav, theme, explorer
├── data/             # read-only Neon access (see data/README.md)
│   ├── __init__.py   # public data API
│   ├── db.py         # engine, fetch_df(), TTL cache, error wrapping
│   ├── queries.py    # SQL + DataFrame shaping
│   ├── schema.py     # static table and column documentation
│   └── README.md     # data-layer reference
└── assets/           # theme.css + logo.svg
tests/
├── test_navigation.py
├── test_data.py
└── test_settings.py
```

## Adding a page

1. **Create the page module** in `src/dash_app/pages/`, exposing a `layout()`
   function that returns Dash components:

   ```python
   # src/dash_app/pages/reports.py
   from dash import html
   from ..components import bulma as b

   def layout():
       return b.section(b.container([b.title("Reports", size=2)]))
   ```

2. **Register it** in `src/dash_app/pages/registry.py`:

   ```python
   from . import reports

   STATIC_PAGES = {
       ...,
       "/reports": Page("Reports", "/reports", reports.layout),
   }
   ```

3. **Add a navigation entry** in `src/dash_app/config.py` (`NAV_LINKS`,
   `ABOUT_MENU`).

4. **Add callbacks** (optional) in `src/dash_app/callbacks/` and register them in
   `callbacks/__init__.py`.

### Dynamic routes

The registry supports `DynamicRoute` for paths such as `/<section>/<id>`. Its layout
receives the remaining path segment. No dynamic routes are registered at the moment.

## Customising the look

- **Branding & nav**: `src/dash_app/config.py`.
- **Colors, spacing, dark theme**: `src/dash_app/assets/theme.css`
  (`--mp-*` CSS variables) plus the `PRIMARY_COLOR` tokens in `config.py`.
- **Logo**: replace `src/dash_app/assets/logo.svg`.

## Data

The app reads `public.cities` and `public.daily` from Neon through a read-only data layer.
All SQL lives in `src/dash_app/data/queries.py`; pages import from `dash_app.data`.

```python
from datetime import date

from dash_app.data import city_daily, list_cities

cities = list_cities()
phoenix = city_daily("phoenix-us", start=date(2020, 1, 1), end=date(2020, 12, 31))
```

The full reference — environment setup, public API, columns, cache TTLs, error handling and
testing rules — is in [`src/dash_app/data/README.md`](src/dash_app/data/README.md).

## Tests

```bash
uv run pytest
```

## License

[MIT](LICENSE)
