"""Home page hero banner."""

from __future__ import annotations

from dash import html

from .. import config
from . import bulma as b

_FEATURES_HREF = next(
    (item.href for item in config.NAV_LINKS if item.label == "Features"),
    "/features",
)


def hero_banner() -> html.Div:
    return html.Div(
        className="mp-hero-banner",
        children=[
            html.H1(config.APP_NAME, className="title is-2 has-text-white"),
            html.P(config.APP_DESCRIPTION, className="subtitle is-5 has-text-white mp-hero-subtitle"),
            b.button(
                "Explore Features",
                href=_FEATURES_HREF,
                color=None,
                className="mp-hero-button",
            ),
        ],
    )
