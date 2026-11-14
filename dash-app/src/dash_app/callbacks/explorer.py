"""Data Explorer callback: bounded daily preview table."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from dash import Input, Output

from ..components import bulma as b
from ..components.tables import data_table
from ..data import PREVIEW_ROWS, DataUnavailable, city_daily_preview

_DAILY_HEADERS = ["Date", "Mean (°C)", "Max (°C)", "Min (°C)"]


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _format_temperature(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "—"


def _daily_rows(frame: pd.DataFrame) -> list[list[Any]]:
    return [
        [
            row.date.strftime("%Y-%m-%d"),
            _format_temperature(row.t_mean),
            _format_temperature(row.t_max),
            _format_temperature(row.t_min),
        ]
        for row in frame.itertuples(index=False)
    ]


def _status_message(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No daily records in this range."
    first = frame["date"].min().strftime("%Y-%m-%d")
    last = frame["date"].max().strftime("%Y-%m-%d")
    return f"Showing {len(frame)} records from {first} to {last}, oldest first."


def build_preview(city_id, start_value, end_value, limit) -> tuple[Any, str]:
    """Return the preview table and status message for the given controls."""
    if not city_id:
        return b.notification("Select a city to preview daily records."), ""

    start = _parse_date(start_value)
    end = _parse_date(end_value)
    if start is not None and end is not None and start > end:
        return (
            b.notification(
                "The start date must be on or before the end date.",
                color="danger",
                light=True,
            ),
            "",
        )

    try:
        frame = city_daily_preview(
            city_id,
            start=start,
            end=end,
            limit=limit or PREVIEW_ROWS,
        )
    except DataUnavailable:
        return (
            b.notification(
                "The daily records could not be loaded. Please try again shortly.",
                color="warning",
                light=True,
            ),
            "",
        )

    return data_table(_DAILY_HEADERS, _daily_rows(frame)), _status_message(frame)


def register(app) -> None:
    @app.callback(
        Output("explorer-daily-table", "children"),
        Output("explorer-daily-status", "children"),
        Input("explorer-city", "value"),
        Input("explorer-start", "value"),
        Input("explorer-end", "value"),
        Input("explorer-limit", "value"),
    )
    def update_daily_preview(city_id, start_value, end_value, limit):
        return build_preview(city_id, start_value, end_value, limit)
