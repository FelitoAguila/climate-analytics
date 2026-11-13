"""Small shared helpers."""

from __future__ import annotations


def is_active(href: str, path: str) -> bool:
    """Return True if ``href`` should be highlighted for the given path."""
    if not href.startswith("/"):
        return False
    if href == "/":
        return path == "/"
    return path == href or path.startswith(f"{href}/")
