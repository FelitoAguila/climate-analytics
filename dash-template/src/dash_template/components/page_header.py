"""Dashboard page header: breadcrumb row plus an icon/title/action row."""

from __future__ import annotations

from typing import Any, Sequence

from dash import html

from . import bulma as b


def page_header(
    title: str,
    breadcrumb: Sequence[tuple[str, str]],
    *,
    icon: str = "fa-solid fa-table-cells",
    action: Any = None,
) -> html.Div:
    return html.Div(
        className="mp-page-header",
        children=[
            b.breadcrumb(breadcrumb),
            html.Div(
                className="mp-page-title-row",
                children=[
                    html.Div(
                        className="mp-page-heading",
                        children=[
                            html.Span(html.I(className=icon), className="icon mp-page-icon"),
                            html.H1(title, className="mp-page-title"),
                        ],
                    ),
                    action,
                ],
            ),
        ],
    )
