"""Application configuration.

This is the primary file to edit when cloning the template: change the
branding, theme tokens and navigation, then add page modules to
``pages/registry.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

APP_NAME = "Dash Template"
APP_SHORT_NAME = "Dash"
APP_DESCRIPTION = (
    "A reusable, content-agnostic Dash application template inspired by the "
    "look and feel of the Materials Project website."
)
APP_AUTHOR = "Dash Template"
APP_COPYRIGHT = "Dash Template"
APP_LICENSE = "MIT"

PRIMARY_COLOR = "hsl(171, 100%, 41%)"
PRIMARY_COLOR_HEX = "#00d1b2"

BULMA_CSS = "https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.4/css/bulma.min.css"
FONT_AWESOME_CSS = (
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"
)
EXTERNAL_STYLESHEETS = [BULMA_CSS, FONT_AWESOME_CSS]

DEFAULT_THEME = "light"


@dataclass(frozen=True)
class NavItem:
    label: str
    href: str
    icon: str | None = None
    external: bool = False


NAV_LINKS: list[NavItem] = [
    NavItem("Features", "/features"),
]

ABOUT_MENU: list[NavItem] = [
    NavItem("About", "/about", "fa-solid fa-circle-info"),
    NavItem("Authors", "/about#authors", "fa-solid fa-users"),
    NavItem("GitHub", "https://github.com/", "fa-brands fa-github", external=True),
    NavItem("Documentation", "https://dash.plotly.com/", "fa-solid fa-book", external=True),
    NavItem("Contact", "mailto:feedback@example.com", "fa-solid fa-envelope", external=True),
]


@dataclass(frozen=True)
class SidebarItem:
    label: str
    icon: str
    active: bool = False


DASHBOARD_NAV: list[list[SidebarItem]] = [
    [SidebarItem("Overview", "fa-solid fa-gauge-high", active=True)],
    [
        SidebarItem("Search", "fa-solid fa-magnifying-glass"),
        SidebarItem("Data Explorer", "fa-solid fa-database"),
    ],
    [
        SidebarItem("Visualizations", "fa-solid fa-chart-line"),
        SidebarItem("Processing", "fa-solid fa-microchip"),
    ],
    [SidebarItem("Settings", "fa-solid fa-sliders")],
]

FOOTER_LINKS: list[tuple[str, str]] = [
    ("Documentation", "https://dash.plotly.com/"),
    ("GitHub", "https://github.com/"),
    ("Contact", "mailto:feedback@example.com"),
]
