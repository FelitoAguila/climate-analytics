"""City map callbacks."""

from __future__ import annotations

from dash import Input, Output, no_update

from ..components.maps import MAP_ID, map_theme_patch


def _is_map_path(pathname: str | None) -> bool:
    return (pathname or "").rstrip("/") == "/map"


def register(app) -> None:
    @app.callback(
        Output(MAP_ID, "figure"),
        Input("theme-store", "data"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )
    def sync_map_theme(theme, pathname):
        if not _is_map_path(pathname):
            return no_update
        return map_theme_patch(theme)
