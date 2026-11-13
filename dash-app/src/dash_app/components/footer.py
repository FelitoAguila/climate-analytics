"""Footer (Materials Project style: links + copyright + licensing line)."""

from __future__ import annotations

from datetime import date

from dash import html

from .. import config


def footer() -> html.Footer:
    year = date.today().year
    links = [
        html.A(name, href=href, target="_blank")
        for name, href in config.FOOTER_LINKS
    ]

    return html.Footer(
        className="footer mp-footer",
        children=[
            html.Div(
                className="content has-text-centered",
                children=[
                    html.P(
                        [
                            html.Strong(config.APP_NAME),
                            html.Span(f" © {year} {config.APP_COPYRIGHT}"),
                        ]
                    ),
                    html.P(links, className="mp-footer-links"),
                    html.P(
                        [
                            "Licensed under ",
                            html.A(
                                config.APP_LICENSE,
                                href="https://opensource.org/licenses/MIT",
                                target="_blank",
                            ),
                            ". Powered by ",
                            html.A("Plotly Dash", href="https://dash.plotly.com/", target="_blank"),
                            " and ",
                            html.A("Bulma", href="https://bulma.io/", target="_blank"),
                            ".",
                        ],
                        className="is-size-7 has-text-grey",
                    ),
                ],
            )
        ],
    )
