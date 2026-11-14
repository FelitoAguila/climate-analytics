"""Data Explorer: table documentation and bounded record previews."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
from dash import dcc, html

from ..components import bulma as b
from ..components.cards import content_card, stat_card, stat_grid
from ..components.page_header import page_header
from ..components.tables import data_table
from ..data import DatasetStatus, DataUnavailable, data_status, list_cities
from ..data.schema import SCHEMAS, TableSchema

_CITY_HEADERS = [
    "id",
    "name",
    "country",
    "code",
    "continent",
    "latitude",
    "longitude",
    "population",
    "capital",
    "coastal",
    "priority",
]


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _text(value: Any) -> str:
    return "—" if _is_missing(value) else str(value)


def _number(value: Any, digits: int = 1) -> str:
    if _is_missing(value):
        return "—"
    return f"{float(value):,.{digits}f}"


def _yes_no(value: Any) -> str:
    if _is_missing(value):
        return "—"
    return "Yes" if bool(value) else "No"


def _schema_card(schema: TableSchema) -> html.Div:
    rows = [
        [column.name, column.type, column.key or "—", column.description]
        for column in schema.columns
    ]
    return content_card(
        f"Table: {schema.name}",
        [
            html.P(schema.summary, className="content"),
            html.P(schema.grain, className="is-size-7 has-text-grey"),
            data_table(
                ["Column", "Type", "Key", "Description"],
                rows,
                max_height="420px",
            ),
        ],
    )


def _city_rows(cities: pd.DataFrame) -> list[list[Any]]:
    return [
        [
            _text(row.id),
            _text(row.name),
            _text(row.country),
            _text(row.country_code),
            _text(row.continent),
            _number(row.latitude, 4),
            _number(row.longitude, 4),
            _number(row.population, 0),
            _yes_no(row.is_capital),
            _yes_no(row.coastal),
            _number(row.priority, 0),
        ]
        for row in cities.itertuples(index=False)
    ]


def _cities_tab(cities: pd.DataFrame | None) -> html.Div:
    children: list[Any] = [_schema_card(SCHEMAS["cities"])]

    if cities is None or cities.empty:
        children.append(
            b.notification(
                [
                    b.title("City records unavailable", size=5),
                    html.P("The city metadata could not be loaded right now."),
                ],
                color="warning",
                light=True,
            )
        )
    else:
        children.append(
            content_card(
                f"City records ({len(cities)})",
                [
                    html.P(
                        "All cities in download order. The table scrolls "
                        "horizontally on small screens.",
                        className="content",
                    ),
                    data_table(_CITY_HEADERS, _city_rows(cities), max_height="520px"),
                ],
            )
        )

    return html.Div(children, className="mp-explorer-stack")


def _field(label: str, control: Any) -> html.Div:
    return html.Div(
        [html.Label(label, className="label"), control],
        className="field",
    )


def _default_city(cities: pd.DataFrame) -> str:
    return str(cities.iloc[0]["id"])


def _default_range(
    cities: pd.DataFrame, status: DatasetStatus, city_id: str
) -> tuple[date | None, date | None]:
    match = status.cities[status.cities["city_id"] == city_id]
    if match.empty:
        return status.first_date, status.latest_date
    last_date = match.iloc[0]["last_date"]
    if _is_missing(last_date):
        return status.first_date, status.latest_date
    end = pd.Timestamp(last_date).date()
    return end - timedelta(days=29), end


def _daily_tab(cities: pd.DataFrame | None, status: DatasetStatus | None) -> html.Div:
    children: list[Any] = [_schema_card(SCHEMAS["daily"])]

    if cities is None or status is None or cities.empty:
        children.append(
            b.notification(
                [
                    b.title("Daily preview unavailable", size=5),
                    html.P("The daily records could not be loaded right now."),
                ],
                color="warning",
                light=True,
            )
        )
        return html.Div(children, className="mp-explorer-stack")

    city_id = _default_city(cities)
    start, end = _default_range(cities, status, city_id)
    min_date = status.first_date.isoformat() if status.first_date else None
    max_date = status.latest_date.isoformat() if status.latest_date else None
    options = [
        {
            "label": f"{_text(row.name)} ({_text(row.country_code)})",
            "value": _text(row.id),
        }
        for row in cities.itertuples(index=False)
    ]

    controls = b.columns(
        [
            b.column(
                _field(
                    "City",
                    dcc.Dropdown(
                        id="explorer-city",
                        options=options,
                        value=city_id,
                        clearable=False,
                        searchable=True,
                    ),
                ),
                size="4",
            ),
            b.column(
                _field(
                    "From",
                    dcc.Input(
                        id="explorer-start",
                        type="date",
                        value=start.isoformat() if start else None,
                        min=min_date,
                        max=max_date,
                        className="input",
                    ),
                ),
                size="3",
            ),
            b.column(
                _field(
                    "To",
                    dcc.Input(
                        id="explorer-end",
                        type="date",
                        value=end.isoformat() if end else None,
                        min=min_date,
                        max=max_date,
                        className="input",
                    ),
                ),
                size="3",
            ),
            b.column(
                _field(
                    "Rows",
                    dcc.Dropdown(
                        id="explorer-limit",
                        options=[
                            {"label": f"{value} rows", "value": value}
                            for value in (10, 25, 50, 100)
                        ],
                        value=25,
                        clearable=False,
                    ),
                ),
                size="2",
            ),
        ],
        multiline=True,
    )

    children.append(
        content_card(
            "Daily records preview",
            [
                html.P(
                    "Choose a city and date range to inspect its most recent "
                    "daily temperatures. Queries are limited to at most 100 rows.",
                    className="content",
                ),
                controls,
                html.P(
                    "Loading preview…",
                    id="explorer-daily-status",
                    className="is-size-7 has-text-grey",
                ),
                dcc.Loading(
                    html.Div(id="explorer-daily-table", children=html.P("Loading…")),
                    type="default",
                ),
            ],
        )
    )
    return html.Div(children, className="mp-explorer-stack")


def _overview(status: DatasetStatus) -> html.Div:
    if status.first_date is None or status.latest_date is None:
        years = "—"
        latest = "—"
    else:
        years = f"{status.first_date.year}–{status.latest_date.year}"
        latest = status.latest_date.strftime("%Y-%m-%d")

    return stat_grid(
        [
            stat_card("Tables", 2, icon="fa-solid fa-table"),
            stat_card("Cities", status.city_count, icon="fa-solid fa-city"),
            stat_card(
                "Daily records",
                f"{status.row_count:,}",
                icon="fa-solid fa-database",
            ),
            stat_card(
                "Latest observation",
                latest,
                icon="fa-solid fa-clock",
                delta=years,
            ),
        ]
    )


def _unavailable_notification() -> html.Div:
    return b.notification(
        [
            b.title("Live data unavailable", size=5),
            html.P(
                "The database could not be reached. The table documentation below "
                "is still available; refresh the page to try the records again."
            ),
        ],
        color="warning",
        light=True,
    )


def layout() -> html.Div:
    try:
        cities: pd.DataFrame | None = list_cities()
        status: DatasetStatus | None = data_status()
    except DataUnavailable:
        cities = None
        status = None

    overview = _overview(status) if status is not None else _unavailable_notification()

    tabs = dcc.Tabs(
        id="explorer-tabs",
        value="cities",
        parent_className="mp-explorer-tabs",
        className="mp-explorer-tabs-nav",
        children=[
            dcc.Tab(
                label="Cities",
                value="cities",
                className="mp-explorer-tab",
                selected_className="mp-explorer-tab is-active",
                children=_cities_tab(cities),
            ),
            dcc.Tab(
                label="Daily",
                value="daily",
                className="mp-explorer-tab",
                selected_className="mp-explorer-tab is-active",
                children=_daily_tab(cities, status),
            ),
        ],
    )

    return html.Div(
        className="mp-explorer",
        children=[
            page_header(
                "Data Explorer",
                [
                    ("Home", "/"),
                    ("Features", "/features"),
                    ("Data Explorer", "/explorer"),
                ],
                icon="fa-solid fa-database",
            ),
            b.section(
                b.container(
                    [
                        b.title("Database overview", size=3),
                        overview,
                        html.P(
                            "The application reads a read-only Neon PostgreSQL "
                            "database populated from ERA5 via Open-Meteo. Each city "
                            "is represented by one ERA5 grid cell of about 25 km, "
                            "not by a weather station.",
                            className="content mp-explorer-intro",
                        ),
                        tabs,
                    ]
                )
            ),
        ],
    )
