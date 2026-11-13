"""Home / dashboard placeholder page."""

from __future__ import annotations

import plotly.express as px
from dash import dcc, html

from .. import config
from ..components import bulma as b
from ..components.cards import feature_card, stat_card, stat_grid
from ..components.search import hero_banner
from ..data import placeholder


def _sample_figure():
    frame = placeholder.records()
    fig = px.bar(
        frame.groupby("category", as_index=False)["score"].sum(),
        x="category",
        y="score",
        color="category",
        labels={"score": "Total score", "category": "Category"},
    )
    fig.update_layout(
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        colorway=[config.PRIMARY_COLOR_HEX],
    )
    return fig


def layout() -> html.Div:
    frame = placeholder.records()
    stats = stat_grid(
        [
            stat_card("Total records", len(frame), icon="fa-solid fa-database"),
            stat_card(
                "Categories",
                frame["category"].nunique(),
                icon="fa-solid fa-layer-group",
            ),
            stat_card(
                "Active",
                int((frame["status"] == "Active").sum()),
                icon="fa-solid fa-bolt",
            ),
            stat_card(
                "Avg. score",
                round(frame["score"].mean(), 2),
                icon="fa-solid fa-chart-line",
            ),
        ]
    )

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
                        b.title("Get started", size=3),
                        features,
                        b.box(
                            [
                                b.title("Example chart", size=5),
                                dcc.Graph(
                                    figure=_sample_figure(),
                                    config={"displayModeBar": False},
                                ),
                            ]
                        ),
                    ]
                )
            ),
        ]
    )
