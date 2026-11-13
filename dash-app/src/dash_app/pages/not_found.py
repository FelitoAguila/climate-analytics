"""404 page."""

from __future__ import annotations

from dash import html

from ..components import bulma as b


def layout() -> html.Div:
    return html.Section(
        className="hero is-medium mp-hero-404",
        children=[
            html.Div(
                className="hero-body",
                children=[
                    b.container(
                        [
                            html.P("404", className="title is-1 has-text-white"),
                            html.P(
                                "The page you are looking for could not be found.",
                                className="subtitle is-5 has-text-white",
                            ),
                            b.button(
                                "Back to home", href="/", color="light", rounded=True
                            ),
                        ],
                        className="has-text-centered",
                    )
                ],
            )
        ],
    )
