"""Home / dashboard page: live database overview and project entry points."""

from __future__ import annotations

from dash import html

from .. import config
from ..components import bulma as b
from ..components.cards import feature_card, stat_card, stat_grid
from ..components.search import hero_banner
from ..data import DataUnavailable, data_status


def _overview_stats() -> html.Div:
    try:
        status = data_status()
    except DataUnavailable:
        return b.notification(
            [
                b.title("Live data unavailable", size=5),
                html.P(
                    "The database summary could not be loaded right now. "
                    "Please try again shortly."
                ),
            ],
            color="warning",
            light=True,
        )

    if status.first_date is None or status.latest_date is None:
        years_value = "—"
        years_detail = "No observations"
        latest_value = "—"
    else:
        years_value = status.latest_date.year - status.first_date.year + 1
        years_detail = f"{status.first_date.year}–{status.latest_date.year}"
        latest_value = (
            f"{status.latest_date.day} {status.latest_date.strftime('%b %Y')}"
        )

    return stat_grid(
        [
            stat_card(
                "Cities",
                status.city_count,
                icon="fa-solid fa-city",
                delta="Complete coverage" if status.cities["complete"].all() else None,
            ),
            stat_card(
                "Daily records",
                f"{status.row_count:,}",
                icon="fa-solid fa-database",
            ),
            stat_card(
                "Years covered",
                years_value,
                icon="fa-solid fa-calendar-days",
                delta=years_detail,
            ),
            stat_card(
                "Latest observation",
                latest_value,
                icon="fa-solid fa-clock",
                delta="ERA5 via Open-Meteo",
            ),
        ]
    )


def layout() -> html.Div:
    stats = _overview_stats()

    features = b.columns(
        [
            b.column(
                feature_card(
                    "Features",
                    "Explore the dashboard and reusable application components.",
                    href="/features",
                    icon="fa-solid fa-table-cells",
                )
            ),
            b.column(
                feature_card(
                    "About the project",
                    "Read about the data, method and authors behind the app.",
                    href="/about",
                    icon="fa-solid fa-circle-info",
                )
            ),
            b.column(
                feature_card(
                    "Source code",
                    "Browse the project on GitHub.",
                    href=config.GITHUB_REPO_URL,
                    icon="fa-brands fa-github",
                )
            ),
        ],
        multiline=True,
    )

    return html.Div(
        [
            html.Section(
                className="hero mp-hero",
                children=[
                    html.Div(
                        className="hero-body", children=[b.container(hero_banner())]
                    )
                ],
            ),
            b.section(
                b.container(
                    [
                        b.title("Overview", size=3),
                        stats,
                        b.title("Get started", size=3, className="mp-home-get-started"),
                        features,
                    ]
                )
            ),
        ]
    )
