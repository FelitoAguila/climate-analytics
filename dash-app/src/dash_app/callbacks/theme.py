"""Light / dark theme toggle with local persistence."""

from __future__ import annotations

from dash import Input, Output, State


def register(app) -> None:
    app.clientside_callback(
        """
        function(n_clicks, theme) {
            if (!n_clicks) {
                return window.dash_clientside.no_update;
            }
            return theme === "dark" ? "light" : "dark";
        }
        """,
        Output("theme-store", "data"),
        Input("theme-toggle", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )

    app.clientside_callback(
        """
        function(theme, pathname) {
            const current = theme || "light";
            document.documentElement.setAttribute("data-theme", current);
            return current;
        }
        """,
        Output("mp-theme-sink", "children"),
        Input("theme-store", "data"),
        Input("url", "pathname"),
    )

    app.clientside_callback(
        """
        function(theme) {
            return theme === "dark"
                ? "fa-solid fa-sun"
                : "fa-solid fa-moon";
        }
        """,
        Output("theme-toggle-icon", "className"),
        Input("theme-store", "data"),
    )
