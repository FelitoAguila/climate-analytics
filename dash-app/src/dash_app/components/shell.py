"""Full-page application shell: navbar + content + footer."""

from __future__ import annotations

from dash import dcc, html

from .. import config
from .footer import footer
from .navbar import navbar


def shell() -> html.Div:
    return html.Div(
        id="mp-app",
        className="mp-app",
        children=[
            dcc.Location(id="url", refresh=False),
            dcc.Store(
                id="theme-store", storage_type="local", data=config.DEFAULT_THEME
            ),
            html.Div(id="mp-theme-sink", style={"display": "none"}),
            html.Div(id="mp-scroll-sink", style={"display": "none"}),
            html.Div(id="page-title", style={"display": "none"}),
            navbar(),
            html.Main(
                id="mp-content",
                className="mp-content",
                children=dcc.Loading(
                    id="page-loading",
                    type="circle",
                    color=config.PRIMARY_COLOR_HEX,
                    parent_className="mp-page-loading",
                    children=html.Div(id="page-content"),
                ),
            ),
            footer(),
        ],
    )
