# AGENTS.md

## Project

`dash-template` — a reusable, **content-agnostic** Plotly Dash application template whose
visual design mirrors the **Materials Project** website (materialsproject.org).

The goal is a clone-and-modify starter: mirror MP's *look, feel, layout and navigation*,
but keep all data/content generic. Cloning should mean editing `config.py` and adding a
page module — not rewriting the shell.

Managed with **uv** (Python >= 3.12). Package lives under `src/dash_template/`.

## Current state

Implemented and passing tests (`uv run pytest`). The template boots via
`uv run dash-template` (or `uv run python -m dash_template`) and renders the MP-style
shell with generic pages.

## Design research (source of truth for the look)

The Materials Project look is not arbitrary — the legacy site and its sibling project are
Dash apps, so there is an authentic precedent to mirror.

- **Crystal Toolkit** (`materialsproject/crystaltoolkit`) is a Dash framework that powered
  `legacy.materialsproject.org`. Its shell = **top navbar + search bar + left sidenav +
  content + footer**.
- Styling is **Bulma 0.9.4** (NOT Bootstrap):
  `https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.4/css/bulma.min.css`
- Icons: **Font Awesome 6.4.2**:
  `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css`
- **Primary color**: `hsl(171, 100%, 41%)` → teal `#00d1b2` (Bulma's default primary).
- `crystal_toolkit/helpers/layouts.py` is the blueprint for reusable Bulma wrappers
  (`Container`, `Columns`/`Column`, `Card*`, `Hero`, `Footer`, `Level`, `Message`,
  `Notification`, `Breadcrumb`, `Tag`, `Table`, headings, etc.).
- MP routes with manual `dcc.Location` + a central `update_main_content` callback
  (see `MPApp.generate_callbacks`) — it does **not** use Dash Pages.
- `materialsproject/mp-react-components` and `materialsproject/dash-mp-components` hold the
  real React/Dash shell components (`MPLayout`, `Navbar`, `SearchUI`), but they are
  materials-science specific and heavyweight (pull in `pymatgen`). **Do not depend on them.**

## Decisions (confirmed with user)

| Topic | Decision |
| --- | --- |
| Visual style | Bulma + custom `theme.css` (authentic MP look), Font Awesome icons |
| Routing | Manual `dcc.Location` + callbacks (mirrors MP), supports dynamic `/<section>/<id>` |
| Dependencies | Minimal: `dash`, `plotly`, `pandas`, `python-dotenv` |
| Scope | Content-agnostic: shell + generic placeholder pages, no materials-specific data |
| Do NOT use | `crystal_toolkit`, `dash-mp-components`, `mp-react-components` |

## Architecture

```
src/dash_template/
├── __init__.py          # main() -> lazy import of app.main
├── __main__.py          # python -m dash_template
├── app.py               # create_app(): Dash instance, external CSS, register layout+callbacks, run()
├── config.py            # APP_* branding, theme tokens, NAV_LINKS, ABOUT_MENU, DASHBOARD_NAV, FOOTER_LINKS
├── utils.py             # is_active(href, path) helper
├── components/
│   ├── bulma.py         # Bulma primitives: container, columns/column, card*, hero, notification, level...
│   ├── shell.py         # full-page shell: navbar + content + footer + dcc.Location/stores
│   ├── navbar.py        # dark navy bar: brand/logo (→ home), Features link, About dropdown, theme toggle, burger
│   ├── sidenav.py       # sidenav(): collapsible icon sidebar (hover/focus expand + tap toggle)
│   ├── page_header.py   # page_header(): breadcrumb + icon/title/action row
│   ├── footer.py
│   ├── search.py        # hero_banner() (hero section without search bar)
│   └── cards.py         # stat_card, feature_card, dashboard_card, content_card, stat_grid
├── pages/
│   ├── registry.py      # path -> (title, nav_key, layout); dynamic-route matching + normalize()
│   ├── home.py          # hero + stat cards + feature card grid + sample Plotly chart
│   ├── features.py      # /features: dashboard (sidebar + page header + card grid)
│   ├── list.py          # generic filterable/sortable table (browse)
│   ├── detail.py        # generic detail page (breadcrumb + cards), reads id from path
│   ├── about.py         # markdown overview
│   └── not_found.py     # 404
├── callbacks/
│   ├── __init__.py      # register_callbacks(app)
│   ├── navigation.py    # pathname -> render page; mobile menu; document title
│   ├── search.py        # browse table filtering; prefill
│   ├── sidenav.py       # sidebar expand/collapse toggle (clientside)
│   └── theme.py         # light/dark toggle with dcc.Store persistence (clientside)
├── data/placeholder.py  # neutral dummy rows (pandas) so the template runs immediately
└── assets/
    ├── theme.css        # MP-inspired overrides + dark theme
    └── logo.svg
tests/
└── test_navigation.py   # registry, filters, active-link, app bootstrap, index smoke test
```

## Look & feel checklist (mirror MP)

- Dark navy (`#202536`) sticky top navbar: logo left, links right (Features, About dropdown, theme toggle), mobile burger.
- No global sidebar in the shell — navigation lives in the navbar (Features link + About dropdown).
- Large centered **hero** section on the home page (no search bar).
- `/features`: dashboard layout — collapsible icon sidebar (hover/focus expand), white page header (breadcrumbs + icon/title/Documentation button) and a responsive feature card grid on `#F3F3F3`.
- Card grid + KPI/stat cards, chips/tags, notifications, breadcrumbs, MP-style tables.
- Footer with links/copyright/licensing line.
- Responsive layout via Bulma `columns` / `is-*` classes.
- Light/dark theme via `html[data-theme]` attribute + CSS variables.

## Callbacks delivered

1. Route rendering (`dcc.Location.pathname` → page content), incl. dynamic `/<section>/<id>` and 404 fallback.
2. Mobile menu burger toggle (off-canvas navbar drawer).
3. Document title sync + `#features` smooth-scroll anchor (clientside).
4. Browse table filtering (text/category/status/sort) + search-filter prefill.
5. Light/dark theme toggle with `dcc.Store`/localStorage persistence (clientside).
6. Features sidebar expand/collapse toggle (clientside; hover/focus handled in CSS).

## Conventions

- Keep everything content-agnostic; use neutral labels/placeholder data.
- Config-driven: add nav items in `config.NAV_LINKS` / `config.ABOUT_MENU` / `config.DASHBOARD_NAV`; add pages in `pages/registry.py`.
- Prefer the `components/bulma.py` helpers over raw Bulma class strings.
- No comments in code unless necessary.
- Don't add materials-science dependencies.
- Never depend on `crystal_toolkit` / `dash-mp-components`.

## Commands

- Install / sync deps: `uv sync`
- Run app: `uv run dash-template` (or `uv run python -m dash_template`)
- Tests: `uv run pytest`
- Lint/format: not yet configured (add if introduced)

## TODO

- [x] Update `pyproject.toml` dependencies and entrypoint.
- [x] Implement `config.py`, `components/`, `pages/`, `callbacks/`, `assets/`.
- [x] Replace `__init__.py:main` with real app bootstrap.
- [x] Add `theme.css` mirroring MP branding and `logo.svg`.
- [x] Write `tests/test_navigation.py`.
- [x] Write README (how to clone & add a page).
- [ ] Optional: configure ruff (lint/format) and add to dev dependencies.
- [ ] Optional: real data source to replace `data/placeholder.py`.
