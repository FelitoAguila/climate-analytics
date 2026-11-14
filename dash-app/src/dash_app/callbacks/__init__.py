"""Callback registration entry point."""

from __future__ import annotations

from . import explorer, navigation, sidenav, theme


def register_callbacks(app) -> None:
    navigation.register(app)
    theme.register(app)
    sidenav.register(app)
    explorer.register(app)
