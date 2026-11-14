"""Collapsible dashboard sidebar.

A narrow, sticky icon sidebar that expands on hover or focus to reveal labels.
Items are real ``dcc.Link`` navigation targets, with the active item derived from
the current page path.
"""

from __future__ import annotations

from dash import dcc, html

from .. import config
from ..utils import is_active


def _item(item: config.SidebarItem, active_href: str | None) -> dcc.Link:
    selected = bool(active_href) and is_active(item.href, active_href)
    classes = "mp-sidenav-item is-selected" if selected else "mp-sidenav-item"
    return dcc.Link(
        [
            html.Span(html.I(className=item.icon), className="icon mp-sidenav-icon"),
            html.Span(item.label, className="mp-sidenav-label"),
        ],
        href=item.href,
        className=classes,
        title=item.label,
    )


def _group(items: list[config.SidebarItem], active_href: str | None) -> html.Div:
    return html.Div(
        [_item(item, active_href) for item in items],
        className="mp-sidenav-group",
    )


def sidenav(
    groups: list[list[config.SidebarItem]], active_href: str | None = None
) -> html.Div:
    nav_children: list[object] = []
    for index, group in enumerate(groups):
        if index:
            nav_children.append(html.Hr(className="mp-sidenav-sep"))
        nav_children.append(_group(group, active_href))

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
