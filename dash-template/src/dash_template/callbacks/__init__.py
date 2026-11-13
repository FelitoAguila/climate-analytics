"""Callback registration entry point."""

from __future__ import annotations

from . import navigation, search, sidenav, theme


def register_callbacks(app) -> None:
    navigation.register(app)
    theme.register(app)
    search.register(app)
    sidenav.register(app)
