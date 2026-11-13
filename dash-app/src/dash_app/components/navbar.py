"""Top navigation bar (Materials Project style: dark navy, sticky, brand left)."""

from __future__ import annotations

from dash import dcc, html

from .. import config


def _item_children(item: config.NavItem) -> list[object]:
    children: list[object] = []
    if item.icon:
        children.append(html.Span(html.I(className=item.icon), className="icon"))
    children.append(html.Span(item.label))
    return children


def nav_links() -> list[object]:
    links: list[object] = []
    for item in config.NAV_LINKS:
        children = _item_children(item)
        if item.external:
            links.append(
                html.A(children, href=item.href, target="_blank", className="navbar-item")
            )
        else:
            links.append(dcc.Link(children, href=item.href, className="navbar-item"))
    return links


def _about_dropdown() -> html.Div:
    items: list[object] = []
    for item in config.ABOUT_MENU:
        children = _item_children(item)
        if item.external:
            items.append(
                html.A(children, href=item.href, target="_blank", className="navbar-item")
            )
        else:
            items.append(dcc.Link(children, href=item.href, className="navbar-item"))

    return html.Div(
        className="navbar-item has-dropdown is-hoverable mp-nav-dropdown",
        id="about-dropdown",
        children=[
            html.A(
                html.Span("About"),
                className="navbar-link",
                id="about-toggle",
                role="button",
            ),
            html.Div(items, className="navbar-dropdown is-right", id="about-menu"),
        ],
    )


def _theme_toggle() -> html.Div:
    return html.Div(
        className="navbar-item",
        children=[
            html.Button(
                html.Span(
                    html.I(className="fa-solid fa-moon", id="theme-toggle-icon"),
                    className="icon",
                ),
                className="button is-light is-rounded",
                id="theme-toggle",
                title="Toggle theme",
            ),
        ],
    )


def _burger() -> html.A:
    return html.A(
        [html.Span(**{"aria-hidden": "true"}) for _ in range(3)],
        role="button",
        className="navbar-burger",
        id="navbar-burger",
        **{"aria-label": "menu", "data-target": "mp-navbar-menu"},
    )


def navbar() -> html.Nav:
    return html.Nav(
        className="navbar mp-navbar is-fixed-top",
        children=[
            html.Div(
                className="navbar-brand",
                children=[
                    dcc.Link(
                        [
                            html.Img(
                                src="/assets/logo.svg",
                                className="mp-logo",
                                alt=config.APP_NAME,
                            ),
                            html.Span(config.APP_NAME, className="mp-brand-name"),
                        ],
                        href="/",
                        className="navbar-item mp-brand",
                    ),
                    _burger(),
                ],
            ),
            html.Div(
                className="navbar-menu",
                id="mp-navbar-menu",
                children=[
                    html.Div(
                        className="navbar-end",
                        children=[
                            *nav_links(),
                            _about_dropdown(),
                            _theme_toggle(),
                        ],
                    ),
                ],
            ),
        ],
    )
