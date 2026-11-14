"""Bulma-styled read-only data tables."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from dash import html


def data_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    id: str | None = None,
    max_height: str | None = None,
) -> html.Div:
    """Render a responsive, horizontally scrollable Bulma table."""
    if not rows:
        kwargs: dict[str, Any] = {
            "children": "No records to display.",
            "className": "notification is-light mp-table-empty",
        }
        if id is not None:
            kwargs["id"] = id
        return html.Div(**kwargs)

    head = html.Thead(html.Tr([html.Th(header, scope="col") for header in headers]))
    body = html.Tbody([html.Tr([html.Td(cell) for cell in row]) for row in rows])
    style = {"maxHeight": max_height, "overflow": "auto"} if max_height else None
    table = html.Table(
        [head, body],
        className="table is-fullwidth is-hoverable is-striped is-narrow",
    )
    kwargs = {
        "children": table,
        "className": "table-container mp-table-wrap",
        "style": style,
    }
    if id is not None:
        kwargs["id"] = id
    return html.Div(**kwargs)
