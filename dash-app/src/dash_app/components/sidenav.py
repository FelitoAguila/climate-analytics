"""Collapsible dashboard sidebar.

A narrow, sticky icon sidebar that expands on hover or focus to reveal labels.
It is presentational: items are non-navigating buttons, so no routes are added.
"""

from __future__ import annotations

from dash import html

from .. import config


def _item(item: config.SidebarItem) -> html.Button:
    classes = "mp-sidenav-item is-selected" if item.active else "mp-sidenav-item"
    aria: dict[str, str] = {"aria-label": item.label}
    if item.active:
        aria["aria-current"] = "true"
    return html.Button(
        [
            html.Span(html.I(className=item.icon), className="icon mp-sidenav-icon"),
            html.Span(item.label, className="mp-sidenav-label"),
        ],
        className=classes,
        type="button",
        title=item.label,
        **aria,
    )


def _group(items: list[config.SidebarItem]) -> html.Div:
    return html.Div([_item(item) for item in items], className="mp-sidenav-group")


def sidenav(groups: list[list[config.SidebarItem]]) -> html.Div:
    nav_children: list[object] = []
    for index, group in enumerate(groups):
        if index:
            nav_children.append(html.Hr(className="mp-sidenav-sep"))
        nav_children.append(_group(group))

    toggle = html.Button(
        html.Span(html.I(className="fa-solid fa-angles-right"), className="icon"),
        className="mp-sidenav-toggle",
        id="mp-sidenav-toggle",
        type="button",
        title="Toggle navigation",
        **{
            "aria-label": "Toggle navigation",
            "aria-expanded": "false",
            "aria-controls": "mp-sidenav",
        },
    )

    return html.Div(
        className="mp-sidenav-slot",
        children=html.Aside(
            [toggle, html.Nav(nav_children, className="mp-sidenav-nav")],
            id="mp-sidenav",
            className="mp-sidenav",
            **{"aria-label": "Section navigation"},
        ),
    )
