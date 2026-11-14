"""City map page: every city in the database on one interactive map."""

from __future__ import annotations

import pandas as pd
from dash import dcc, html

from ..components import bulma as b
from ..components.cards import content_card, stat_card, stat_grid
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
                    "Scroll to zoom, drag to pan, and hover over a city to see "
                    "its details.",
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
        section_children.extend([_stats(cities), _map_card(cities)])

    children.append(b.section(b.container(section_children)))
    return html.Div(className="mp-map-page", children=children)
