# dash-app

A reusable, **content-agnostic** [Plotly Dash](https://dash.plotly.com/) application
template whose visual design is inspired by the
[Materials Project](https://materialsproject.org) website.

It gives you the shell and look-and-feel — top navbar, hero section, cards, tables, tags,
breadcrumbs, footer and a light/dark theme — so you can focus on your own content. Clone it,
edit `config.py`, add a page module, and go.

## Features

- Materials Project inspired layout built on **Bulma** + **Font Awesome**.
- Manual `dcc.Location` routing with callbacks (supports dynamic `/<section>/<id>`).
- Reusable, dependency-light Bulma helpers (`components/bulma.py`).
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
uv run dash-app        # or: uv run python -m dash_app
```

Then open <http://localhost:8050>.

Environment variables (all optional):

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8050` | Port |
| `DASH_DEBUG` | `true` | Enable Dash debug mode |

## Project layout

```
src/dash_app/
├── app.py            # create_app() factory + entry point
├── config.py         # branding, theme tokens, navigation
├── utils.py          # is_active() helper
├── components/       # shell, navbar, sidenav, page header, footer, search, cards, Bulma helpers
├── pages/            # page layouts + registry
├── callbacks/        # navigation, search, sidenav, theme
├── data/placeholder.py
└── assets/           # theme.css + logo.svg
tests/
└── test_navigation.py
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

All content is placeholder and lives in `src/dash_app/data/placeholder.py`
(a small pandas DataFrame). Replace it with your own data source; nothing else depends on
its specifics beyond the browse/detail pages.

## Tests

```bash
uv run pytest
```

## License

MIT
