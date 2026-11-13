"""Project footer: navigation, data attribution and licensing."""

from __future__ import annotations

from datetime import date

from dash import dcc, html

from .. import config


def _link(item: config.NavItem) -> object:
    if item.external:
        return html.A(
            item.label,
            href=item.href,
            target="_blank",
            rel="noopener",
        )
    return dcc.Link(item.label, href=item.href)


def footer() -> html.Footer:
    year = date.today().year
    links = [_link(item) for item in config.FOOTER_LINKS]

    return html.Footer(
        className="footer mp-footer",
        children=[
            html.Div(
                className="content has-text-centered",
                children=[
                    html.P(
                        [
                            html.Strong(config.FOOTER_TITLE),
                            html.Span(f" © {year}"),
                        ]
                    ),
                    html.P(links, className="mp-footer-links"),
                    html.P(
                        [
                            "Daily temperatures from ",
                            html.A(
                                "ERA5 reanalysis via Open-Meteo",
                                href="https://open-meteo.com/en/docs/historical-weather-api",
                                target="_blank",
                                rel="noopener",
                            ),
                            " (CC BY 4.0). City data from ",
                            html.A(
                                "Natural Earth",
                                href="https://www.naturalearthdata.com/",
                                target="_blank",
                                rel="noopener",
                            ),
                            ".",
                        ],
                        className="is-size-7 has-text-grey",
                    ),
                    html.P(
                        [
                            "Licensed under ",
                            html.A(
                                config.APP_LICENSE,
                                href="https://opensource.org/licenses/MIT",
                                target="_blank",
                                rel="noopener",
                            ),
                            ". Built with ",
                            html.A(
                                "Plotly Dash",
                                href="https://dash.plotly.com/",
                                target="_blank",
                                rel="noopener",
                            ),
                            " and ",
                            html.A(
                                "Bulma",
                                href="https://bulma.io/",
                                target="_blank",
                                rel="noopener",
                            ),
                            ".",
                        ],
                        className="is-size-7 has-text-grey",
                    ),
                ],
            )
        ],
    )
