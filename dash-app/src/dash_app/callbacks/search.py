"""Global search navigation and the generic browse table filtering."""

from __future__ import annotations

from urllib.parse import parse_qs, quote

import pandas as pd
from dash import Input, Output

from ..data import placeholder
from ..pages import list as list_page

_SORT_KEYS = {
    "score_desc": ("score", False),
    "score_asc": ("score", True),
    "name_asc": ("name", True),
    "updated_desc": ("updated", False),
}


def _sort(frame: pd.DataFrame, sort_key: str | None) -> pd.DataFrame:
    column, ascending = _SORT_KEYS.get(sort_key or "", ("score", False))
    return frame.sort_values(column, ascending=ascending)


def apply_filters(
    frame: pd.DataFrame,
    text: str | None = None,
    category: str | None = None,
    status: str | None = None,
    sort_key: str | None = None,
) -> pd.DataFrame:
    frame = frame.copy()
    if text:
        mask = frame["name"].str.contains(text, case=False, na=False) | frame[
            "id"
        ].str.contains(text, case=False, na=False)
        frame = frame[mask]
    if category:
        frame = frame[frame["category"] == category]
    if status:
        frame = frame[frame["status"] == status]
    return _sort(frame, sort_key)


def build_search_href(term: str | None) -> str | None:
    term = (term or "").strip()
    if not term:
        return None
    return f"/browse?q={quote(term)}"


def register(app) -> None:
    @app.callback(
        Output("browse-table-body", "children"),
        Output("browse-count", "children"),
        Input("browse-filter", "value"),
        Input("browse-category", "value"),
        Input("browse-status", "value"),
        Input("browse-sort", "value"),
    )
    def filter_table(text, category, status, sort_key):
        frame = apply_filters(placeholder.records(), text, category, status, sort_key)
        return list_page.table_rows(frame), str(len(frame))

    @app.callback(
        Output("browse-filter", "value"),
        Input("url", "search"),
    )
    def prefill_filter(search):
        if not search:
            return ""
        params = parse_qs(search.lstrip("?"))
        return (params.get("q") or [""])[0]
