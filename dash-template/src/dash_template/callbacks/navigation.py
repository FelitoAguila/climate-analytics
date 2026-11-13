"""Routing, mobile menu, document title and anchor scrolling."""

from __future__ import annotations

from dash import Input, Output, State, no_update

from .. import config
from ..pages import registry


def register(app) -> None:
    @app.callback(
        Output("page-content", "children"),
        Output("page-title", "children"),
        Input("url", "pathname"),
    )
    def render_page(pathname):
        resolved = registry.resolve(pathname)
        return resolved.layout, resolved.title

    @app.callback(
        Output("mp-navbar-menu", "className"),
        Output("navbar-burger", "className"),
        Input("navbar-burger", "n_clicks"),
        State("mp-navbar-menu", "className"),
        prevent_initial_call=True,
    )
    def toggle_mobile_menu(n_clicks, menu_class):
        if not n_clicks:
            return no_update, no_update
        is_open = "is-active" in (menu_class or "").split()
        if is_open:
            return "navbar-menu", "navbar-burger"
        return "navbar-menu is-active", "navbar-burger is-active"

    app.clientside_callback(
        """
        function(title) {
            if (title) {
                document.title = title + " · " + %s;
            }
            return window.dash_clientside.no_update;
        }
        """
        % repr(config.APP_NAME),
        Output("page-title", "className"),
        Input("page-title", "children"),
    )

    app.clientside_callback(
        """
        function(hash) {
            if (hash) {
                const id = hash.replace("#", "");
                setTimeout(function () {
                    const el = document.getElementById(id);
                    if (el) {
                        el.scrollIntoView({behavior: "smooth", block: "start"});
                    }
                }, 50);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("mp-scroll-sink", "children"),
        Input("url", "hash"),
        prevent_initial_call=True,
    )
