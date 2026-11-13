"""About page (generic markdown overview)."""

from __future__ import annotations

from dash import dcc, html

from .. import config
from ..components import bulma as b

_OVERVIEW = f"""
## About {config.APP_NAME}

{config.APP_DESCRIPTION}

This template mirrors the general look and feel of the
[Materials Project](https://materialsproject.org) website:

- a dark navy **top navbar** with brand, links, About dropdown and theme toggle
- a large centered **hero** on the home page
- a **`/features`** page laid out as a dashboard: collapsible icon sidebar,
  page header with breadcrumbs and a responsive feature card grid
- **cards**, **tables**, **tags**, **breadcrumbs** and **notifications**
- a themed, responsive layout built on [Bulma](https://bulma.io/)

### Adding a page

1. Create a module in `pages/` that exposes a `layout()` function.
2. Register it in `pages/registry.py`.
3. Add a navigation entry in `config.py`.

Everything is content-agnostic: swap the placeholder data in
`data/placeholder.py` for your own and restyle via `assets/theme.css`.
"""


def layout() -> html.Div:
    return b.section(
        b.container(
            [
                b.breadcrumb([("Home", "/"), ("About", "/about")]),
                b.box(dcc.Markdown(_OVERVIEW, className="content")),
            ],
            **{"style": {"maxWidth": "900px"}},
        )
    )
