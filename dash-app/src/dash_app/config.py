"""Application configuration.

This is the primary file to edit when cloning the template: change the
branding, theme tokens and navigation, then add page modules to
``pages/registry.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

APP_NAME = "Climate Analytics"
APP_SHORT_NAME = "Climate"
APP_DESCRIPTION = (
    "Explore how temperatures have changed in 140 cities since 1940, using "
    "daily ERA5 data from Open-Meteo."
)
APP_AUTHOR = "Climate Analytics"
APP_COPYRIGHT = "Climate Analytics"
APP_LICENSE = "MIT"

PRIMARY_COLOR = "hsl(171, 100%, 41%)"
PRIMARY_COLOR_HEX = "#00d1b2"

BULMA_CSS = "https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.4/css/bulma.min.css"
FONT_AWESOME_CSS = (
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"
)
EXTERNAL_STYLESHEETS = [BULMA_CSS, FONT_AWESOME_CSS]

DEFAULT_THEME = "light"

GITHUB_REPO_URL = "https://github.com/FelitoAguila/climate-analytics"
OPEN_METEO_URL = "https://open-meteo.com/en/docs/historical-weather-api"


@dataclass(frozen=True)
class NavItem:
    label: str
    href: str
    icon: str | None = None
    external: bool = False


@dataclass(frozen=True)
class Author:
    name: str
    links: tuple[NavItem, ...]


NAV_LINKS: list[NavItem] = [
    NavItem("Features", "/features"),
    NavItem("Data Explorer", "/explorer", "fa-solid fa-database"),
]

ABOUT_MENU: list[NavItem] = [
    NavItem("About", "/about", "fa-solid fa-circle-info"),
    NavItem("Authors", "/about#authors", "fa-solid fa-users"),
    NavItem(
        "GitHub",
        GITHUB_REPO_URL,
        "fa-brands fa-github",
        external=True,
    ),
]

AUTHORS: tuple[Author, ...] = (
    Author(
        "Felix Manuel Aguila Alonso",
        (
            NavItem(
                "GitHub",
                "https://github.com/FelitoAguila",
                "fa-brands fa-github",
                external=True,
            ),
            NavItem(
                "LinkedIn",
                "https://www.linkedin.com/in/felix-aguila",
                "fa-brands fa-linkedin",
                external=True,
            ),
            NavItem(
                "Website",
                "https://felitoaguila.github.io/",
                "fa-solid fa-globe",
                external=True,
            ),
        ),
    ),
    Author(
        "Albert Alain Valdivia Garcia",
        (
            NavItem(
                "GitHub",
                "https://github.com/tcpalbertvaldivia1993-lang",
                "fa-brands fa-github",
                external=True,
            ),
            NavItem(
                "LinkedIn",
                "https://www.linkedin.com/in/albert-valdivia-656156445/",
                "fa-brands fa-linkedin",
                external=True,
            ),
            NavItem(
                "Website",
                "https://tcpalbertvaldivia1993-lang.github.io/",
                "fa-solid fa-globe",
                external=True,
            ),
        ),
    ),
)


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

FOOTER_TITLE = APP_COPYRIGHT
FOOTER_LINKS: list[NavItem] = [
    NavItem("Home", "/"),
    NavItem("About", "/about"),
    NavItem("Authors", "/about#authors"),
    NavItem("GitHub", GITHUB_REPO_URL, external=True),
    NavItem("Open-Meteo data", OPEN_METEO_URL, external=True),
]
