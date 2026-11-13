"""dash-template: a reusable, content-agnostic Plotly Dash template."""

from __future__ import annotations

__all__ = ["main"]


def main() -> None:
    from .app import main as _main

    _main()
