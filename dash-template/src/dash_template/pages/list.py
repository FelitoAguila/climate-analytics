"""Generic filterable / sortable list page."""

from __future__ import annotations

import pandas as pd
from dash import dcc, html

from ..components import bulma as b
from ..data import placeholder

_SORT_OPTIONS = [
    {"label": "Score (high → low)", "value": "score_desc"},
    {"label": "Score (low → high)", "value": "score_asc"},
    {"label": "Name (A → Z)", "value": "name_asc"},
    {"label": "Recently updated", "value": "updated_desc"},
]


def _status_tag(status: str) -> html.Span:
    color = {"Active": "success", "Pending": "warning", "Archived": "light"}.get(status, "info")
    return b.tag(status, color=color, rounded=True, light=True)


def table_rows(frame: pd.DataFrame) -> list[html.Tr]:
    rows = []
    for record in frame.to_dict("records"):
        rows.append(
            html.Tr(
                [
                    html.Td(
                        dcc.Link(
                            record["id"],
                            href=f"/browse/{record['id']}",
                            className="mp-table-link",
                        )
                    ),
                    html.Td(record["name"]),
                    html.Td(record["category"]),
                    html.Td(_status_tag(record["status"])),
                    html.Td(f"{record['score']:.2f}"),
                    html.Td(record["updated"]),
                ]
            )
        )
    return rows


def _controls() -> html.Div:
    return b.box(
        b.columns(
            [
                b.column(
                    [
                        html.Label("Search", className="label"),
                        dcc.Input(
                            id="browse-filter",
                            type="text",
                            placeholder="Filter by name or id...",
                            className="input",
                            debounce=True,
                        ),
                    ],
                    size="is-4",
                ),
                b.column(
                    [
                        html.Label("Category", className="label"),
                        dcc.Dropdown(
                            id="browse-category",
                            options=[{"label": c, "value": c} for c in placeholder.categories()],
                            placeholder="All",
                        ),
                    ]
                ),
                b.column(
                    [
                        html.Label("Status", className="label"),
                        dcc.Dropdown(
                            id="browse-status",
                            options=[{"label": s, "value": s} for s in placeholder.statuses()],
                            placeholder="All",
                        ),
                    ]
                ),
                b.column(
                    [
                        html.Label("Sort by", className="label"),
                        dcc.Dropdown(
                            id="browse-sort",
                            options=_SORT_OPTIONS,
                            value="score_desc",
                            clearable=False,
                        ),
                    ]
                ),
            ],
            multiline=True,
        )
    )


def _table(frame: pd.DataFrame) -> html.Div:
    header = html.Thead(
        html.Tr(
            [
                html.Th("ID"),
                html.Th("Name"),
                html.Th("Category"),
                html.Th("Status"),
                html.Th("Score"),
                html.Th("Updated"),
            ]
        )
    )
    body = html.Tbody(table_rows(frame), id="browse-table-body")
    return html.Div(
        html.Table([header, body], className="table is-fullwidth is-hoverable is-striped"),
        className="table-container",
    )


def layout() -> html.Div:
    frame = placeholder.records()
    return b.section(
        b.container(
            [
                b.breadcrumb([("Home", "/"), ("Browse", "/browse")]),
                b.title("Browse", size=2),
                html.P(
                    [html.Span("Showing "), html.Strong(str(len(frame)), id="browse-count"), html.Span(" records")],
                    className="subtitle is-6 has-text-grey",
                ),
                _controls(),
                _table(frame),
            ]
        )
    )
