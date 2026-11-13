"""Generic detail page, driven by a record id parsed from the URL."""

from __future__ import annotations

import plotly.graph_objects as go
from dash import dcc, html

from .. import config
from ..components import bulma as b
from ..data import placeholder


def _detail_table(record: dict) -> html.Table:
    labels = {
        "id": "Identifier",
        "name": "Name",
        "category": "Category",
        "status": "Status",
        "score": "Score",
        "updated": "Updated",
    }
    rows = [
        html.Tr([html.Th(labels.get(key, key), className="has-text-grey"), html.Td(value)])
        for key, value in record.items()
    ]
    return html.Table(html.Tbody(rows), className="table is-narrow is-fullwidth mp-detail-table")


def _radial(score: float) -> dcc.Graph:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "", "font": {"size": 36}},
            gauge={
                "axis": {"range": [0, 10]},
                "bar": {"color": config.PRIMARY_COLOR_HEX},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
            },
        )
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=10),
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


def layout(record_id: str) -> html.Div:
    record = placeholder.get_record(record_id)

    if record is None:
        return b.section(
            b.container(
                [
                    b.breadcrumb([("Home", "/"), ("Browse", "/browse"), (record_id, "#")]),
                    b.notification(
                        [
                            b.title("Record not found", size=4),
                            html.P(f'No record with identifier "{record_id}" exists.'),
                            b.button("Back to browse", href="/browse"),
                        ],
                        color="warning",
                        light=True,
                    ),
                ]
            )
        )

    return b.section(
        b.container(
            [
                b.breadcrumb(
                    [
                        ("Home", "/"),
                        ("Browse", "/browse"),
                        (record["name"], f"/browse/{record['id']}"),
                    ]
                ),
                b.title(record["name"], size=2),
                b.tags(
                    [
                        b.tag(record["category"], color="primary", rounded=True, light=True),
                        b.tag(record["status"], color="info", rounded=True, light=True),
                    ]
                ),
                b.columns(
                    [
                        b.column(
                            b.card(
                                [
                                    b.card_header([b.card_header_title("Details")]),
                                    b.card_content(_detail_table(record)),
                                ]
                            )
                        ),
                        b.column(
                            b.card(
                                [
                                    b.card_header([b.card_header_title("Score")]),
                                    b.card_content(_radial(float(record["score"]))),
                                ]
                            )
                        ),
                    ]
                ),
            ]
        )
    )
