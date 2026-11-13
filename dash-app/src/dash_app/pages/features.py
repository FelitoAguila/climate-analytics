"""Features page: scientific dashboard layout.

Composes the shared navbar (from the shell) with a collapsible left sidebar, a
breadcrumb/page header and a responsive grid of reusable feature cards.
"""

from __future__ import annotations

from dash import html

from .. import config
from ..components.cards import dashboard_card
from ..components.page_header import page_header
from ..components.sidenav import sidenav

_DOCS_URL = "https://dash.plotly.com/"

_CARDS = [
    ("Data Explorer", "Explore datasets and inspect records.", "fa-solid fa-database"),
    ("Analytics Dashboard", "Visualize metrics and discover trends.", "fa-solid fa-chart-line"),
    ("Data Search", "Search and filter data using configurable criteria.", "fa-solid fa-magnifying-glass"),
    ("Data Visualization", "Explore data through charts and interactive plots.", "fa-solid fa-chart-pie"),
    ("Data Processing", "Discover data transformation and processing tools.", "fa-solid fa-microchip"),
    ("API Explorer", "Inspect available endpoints and data resources.", "fa-solid fa-code"),
    ("Reports", "Browse summaries and generated reports.", "fa-solid fa-file-lines"),
    ("Settings", "Configure application preferences.", "fa-solid fa-sliders"),
]


def _documentation_button() -> html.A:
    return html.A(
        [
            html.Span(html.I(className="fa-solid fa-book"), className="icon"),
            html.Span("Documentation"),
        ],
        href=_DOCS_URL,
        target="_blank",
        rel="noopener",
        className="mp-doc-button",
    )


def _card_grid() -> html.Div:
    return html.Div(
        [dashboard_card(title, description, icon=icon) for title, description, icon in _CARDS],
        className="mp-feature-grid",
    )


def layout() -> html.Div:
    return html.Div(
        className="mp-dashboard",
        children=[
            sidenav(config.DASHBOARD_NAV),
            html.Div(
                className="mp-dashboard-main",
                children=[
                    page_header(
                        "Features",
                        [("Home", "/"), ("Features", "/features")],
                        action=_documentation_button(),
                    ),
                    html.Div(
                        className="mp-dashboard-body",
                        children=[
                            html.H2("Explore Features", className="mp-section-title"),
                            _card_grid(),
                        ],
                    ),
                ],
            ),
        ],
    )
