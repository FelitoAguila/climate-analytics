"""City map page: every city in the database on one interactive map."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from dash import dcc, html

from .. import config
from ..components import bulma as b
from ..components.cards import content_card, stat_card, stat_grid
from ..components.distributions import (
    VARIABLES,
    empty_distribution_figure,
    year_marks,
)
from ..components.maps import MAP_ID, build_city_map
from ..components.page_header import page_header
from ..data import DataUnavailable, list_cities


def _stats(cities: pd.DataFrame) -> html.Div:
    continents = int(cities["continent"].nunique(dropna=True))
    countries = int(cities["country"].nunique(dropna=True))
    return stat_grid(
        [
            stat_card("Cities", len(cities), icon="fa-solid fa-city"),
            stat_card("Continents", continents, icon="fa-solid fa-earth-americas"),
            stat_card("Countries", countries, icon="fa-solid fa-flag"),
        ]
    )


def _map_card(cities: pd.DataFrame) -> html.Div:
    figure = build_city_map(cities, theme="light")
    return html.Div(
        content_card(
            "World map",
            [
                html.P(
                    "All cities use the same marker. Use the legend to hide or "
                    "show continents.",
                    className="content",
                ),
                dcc.Graph(
                    id=MAP_ID,
                    figure=figure,
                    className="mp-city-map",
                    style={"height": "68vh", "minHeight": "460px"},
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "responsive": True,
                        "scrollZoom": True,
                    },
                ),
                html.P(
                    "Scroll to zoom, drag to pan, and hover over a city for "
                    "details. Use the city filter below to explore its annual "
                    "temperature distributions.",
                    className="is-size-7 has-text-grey mp-map-hint",
                ),
            ],
        ),
        className="mp-map-card",
    )


def _unavailable_notification() -> html.Div:
    return b.notification(
        [
            b.title("Map unavailable", size=5),
            html.P(
                "The city metadata could not be loaded right now. "
                "Please try again shortly."
            ),
        ],
        color="warning",
        light=True,
    )


def _field(label: str, control: Any) -> html.Div:
    return html.Div(
        [html.Label(label, className="label"), control],
        className="field",
    )


def _distribution_card(cities: pd.DataFrame) -> html.Div:
    current_year = date.today().year
    options = [
        {
            "label": f"{row.name} ({row.country_code})",
            "value": row.id,
        }
        for row in cities.itertuples(index=False)
    ]
    return html.Div(
        content_card(
            "Annual temperature distributions",
            [
                html.P(
                    "Choose a city, temperature variable and year range. Each "
                    "ridge is a kernel density estimate of that year's daily "
                    "temperatures; every year with available values is included, "
                    "even if it is incomplete.",
                    className="content",
                ),
                html.H4(
                    "Select a city",
                    id="distribution-city",
                    className="mp-distribution-city",
                ),
                b.columns(
                    [
                        b.column(
                            _field(
                                "City",
                                dcc.Dropdown(
                                    id="city-filter",
                                    options=options,
                                    value=None,
                                    placeholder="Select a city",
                                    clearable=True,
                                    searchable=True,
                                ),
                            ),
                            size="4",
                        ),
                        b.column(
                            _field(
                                "Temperature",
                                dcc.RadioItems(
                                    id="temperature-variable",
                                    options=[
                                        {"label": label, "value": value}
                                        for value, label in VARIABLES.items()
                                    ],
                                    value="t_mean",
                                    inline=True,
                                    className="mp-temperature-options",
                                ),
                            ),
                            size="3",
                        ),
                        b.column(
                            _field(
                                "Years",
                                dcc.RangeSlider(
                                    id="year-range",
                                    min=1940,
                                    max=current_year,
                                    step=1,
                                    value=[1940, current_year],
                                    marks=year_marks(1940, current_year),
                                    disabled=True,
                                    allowCross=False,
                                    updatemode="mouseup",
                                    tooltip={
                                        "placement": "bottom",
                                        "always_visible": False,
                                    },
                                    className="mp-year-slider",
                                ),
                            ),
                            size="5",
                        ),
                    ],
                    multiline=True,
                    className="mp-distribution-controls",
                ),
                html.P(
                    "Choose a city to load its annual distributions.",
                    id="distribution-status",
                    className="is-size-7 has-text-grey",
                ),
                dcc.Loading(
                    dcc.Graph(
                        id="distribution-chart",
                        figure=empty_distribution_figure("light"),
                        className="mp-distribution-chart",
                        config={
                            "displayModeBar": True,
                            "displaylogo": False,
                            "responsive": True,
                        },
                    ),
                    type="circle",
                    color=config.PRIMARY_COLOR_HEX,
                ),
            ],
        ),
        className="mp-distribution-card",
    )


def layout() -> html.Div:
    try:
        cities: pd.DataFrame | None = list_cities()
    except DataUnavailable:
        cities = None

    children = [
        page_header(
            "City Map",
            [("Home", "/"), ("Features", "/features"), ("City Map", "/map")],
            icon="fa-solid fa-earth-americas",
        )
    ]

    section_children = [
        b.title("Every city on one map", size=3),
        html.P(
            "Explore every city in the database and the regions they cover. "
            "Each marker is one city; the underlying temperature data is one ERA5 "
            "grid cell of about 25 km.",
            className="content mp-map-intro",
        ),
    ]

    if cities is None or cities.empty:
        section_children.append(_unavailable_notification())
    else:
        section_children.extend(
            [_stats(cities), _map_card(cities), _distribution_card(cities)]
        )

    children.append(b.section(b.container(section_children)))
    return html.Div(className="mp-map-page", children=children)
