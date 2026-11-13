"""Sidebar expand/collapse toggle for pointer-unfriendly devices and keyboards."""

from __future__ import annotations

from dash import Input, Output, State


def register(app) -> None:
    app.clientside_callback(
        """
        function(n_clicks, current) {
            if (!n_clicks) {
                return [window.dash_clientside.no_update, window.dash_clientside.no_update];
            }
            const open = (current || "").indexOf("is-open") !== -1;
            const base = (current || "").replace(/\\s*is-open/g, "").trim();
            return [open ? base : (base + " is-open").trim(), open ? "false" : "true"];
        }
        """,
        Output("mp-sidenav", "className"),
        Output("mp-sidenav-toggle", "aria-expanded"),
        Input("mp-sidenav-toggle", "n_clicks"),
        State("mp-sidenav", "className"),
        prevent_initial_call=True,
    )
