"""dash-app: the climate-analytics Plotly Dash web application."""

from __future__ import annotations

__all__ = ["main"]


def main() -> None:
    from .app import main as _main

    _main()
