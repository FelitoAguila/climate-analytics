"""Page registry: maps URL paths to page layouts.

To add a page, create a module exposing a ``layout()`` function and register it
here. Dynamic routes (e.g. ``/browse/<id>``) receive the remaining path segment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import about, detail, features, home, list as list_page, not_found


@dataclass(frozen=True)
class Page:
    title: str
    nav_key: str | None
    layout: Callable[..., Any]


@dataclass(frozen=True)
class DynamicRoute:
    prefix: str
    title: str
    nav_key: str | None
    layout: Callable[[str], Any]

    def match(self, pathname: str) -> str | None:
        if not pathname.startswith(self.prefix):
            return None
        remainder = pathname[len(self.prefix):]
        return remainder or None


STATIC_PAGES: dict[str, Page] = {
    "/": Page("Dashboard", "/", home.layout),
    "/browse": Page("Browse", "/browse", list_page.layout),
    "/about": Page("About", "/about", about.layout),
    "/features": Page("Features", "/features", features.layout),
}

DYNAMIC_ROUTES: list[DynamicRoute] = [
    DynamicRoute("/browse/", "Record detail", "/browse", detail.layout),
]


@dataclass(frozen=True)
class Resolved:
    title: str
    nav_key: str | None
    layout: Any
    found: bool


def normalize(pathname: str | None) -> str:
    pathname = (pathname or "/").split("?")[0]
    if len(pathname) > 1 and pathname.endswith("/"):
        pathname = pathname.rstrip("/")
    return pathname or "/"


def resolve(pathname: str | None) -> Resolved:
    path = normalize(pathname)

    if path in STATIC_PAGES:
        page = STATIC_PAGES[path]
        return Resolved(page.title, page.nav_key, page.layout(), True)

    for route in DYNAMIC_ROUTES:
        dynamic_id = route.match(path)
        if dynamic_id:
            return Resolved(route.title, route.nav_key, route.layout(dynamic_id), True)

    return Resolved("Not found", None, not_found.layout(), False)
