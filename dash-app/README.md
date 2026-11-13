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
- Generic placeholder pages: dashboard, filterable list, detail, about and a 404.
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

### Deploying to Render

Set `READONLY_DATABASE_URL` in Render's Environment tab as a secret, set
`DASH_DEBUG=false`, and let Render provide `PORT`. Do not upload `.env`. Use a production
server such as Gunicorn with `dash_app.app:server`.

## Project layout

```
src/dash_app/
├── app.py            # create_app() factory + entry point
├── settings.py       # explicit .env loading + database URL handling
├── errors.py         # DataLayerError, ConfigurationError, DataUnavailable
├── config.py         # branding, theme tokens, navigation
├── utils.py          # is_active() helper
├── components/       # shell, navbar, sidenav, page header, footer, search, cards, Bulma helpers
├── pages/            # page layouts + registry
├── callbacks/        # navigation, search, sidenav, theme
├── data/             # read-only Neon access (see data/README.md)
│   ├── __init__.py   # public data API
│   ├── db.py         # engine, fetch_df(), TTL cache, error wrapping
│   ├── queries.py    # SQL + DataFrame shaping
│   ├── README.md     # data-layer reference
│   └── placeholder.py
└── assets/           # theme.css + logo.svg
tests/
├── test_navigation.py
└── test_data.py
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

`/browse/<id>` is served by a `DynamicRoute` in the registry. Its layout receives the
remaining path segment:

```python
def layout(record_id: str):
    ...
```

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

The template's placeholder pages still read `data/placeholder.py` until they are migrated.

## Tests

```bash
uv run pytest
```

## License

MIT
