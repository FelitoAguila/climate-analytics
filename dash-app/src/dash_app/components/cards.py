"""Reusable card components (stat, feature, dashboard and content cards)."""

from __future__ import annotations

from typing import Any

from dash import html

from . import bulma as b


def stat_card(label: str, value: Any, *, icon: str | None = None, delta: str | None = None) -> html.Div:
    icon_el = (
        html.Span(html.I(className=icon), className="icon is-large mp-stat-icon")
        if icon
        else None
    )
    return b.card(
        b.card_content(
            b.columns(
                [
                    b.column(
                        [
                            html.P(label, className="heading has-text-grey"),
                            html.P(str(value), className="title is-3 mp-stat-value"),
                            (
                                html.P(delta, className="is-size-7 has-text-success")
                                if delta
                                else None
                            ),
                        ]
                    ),
                    (
                        b.column(icon_el, size="is-narrow") if icon_el is not None else None
                    ),
                ],
                className="is-vcentered",
            )
        ),
        className="mp-stat-card",
    )


def feature_card(title: str, description: str, href: str = "#", *, icon: str | None = None) -> html.Div:
    return b.card(
        [
            b.card_content(
                [
                    (
                        html.Span(html.I(className=icon), className="icon is-large mp-feature-icon")
                        if icon
                        else None
                    ),
                    html.P(title, className="title is-5"),
                    html.P(description, className="content has-text-grey"),
                ]
            ),
            b.card_footer([b.card_footer_item("Open", href=href)]),
        ],
        className="mp-feature-card",
    )


def dashboard_card(title: str, description: str, *, icon: str | None = None) -> html.Div:
    icon_el = (
        html.Span(html.I(className=icon), className="icon mp-dash-icon")
        if icon
        else None
    )
    return html.Div(
        [
            icon_el,
            html.P(title, className="mp-dash-title"),
            html.P(description, className="mp-dash-desc"),
        ],
        className="mp-dash-card",
    )


def content_card(title: str, children: Any, *, footer: Any = None) -> html.Div:
    body = [b.card_header([b.card_header_title(title)])]
    body.append(b.card_content(children))
    if footer is not None:
        body.append(b.card_footer(footer))
    return b.card(body, className="mp-content-card")


def linked_content_card(title: str, children: Any, href: str) -> html.Div:
    return b.card(
        [
            b.card_header([b.card_header_title(title)]),
            b.card_content(children),
            b.card_footer([b.card_footer_item("View details", href=href)]),
        ],
        className="mp-content-card",
    )


def stat_grid(cards: list[Any]) -> html.Div:
    return b.columns([b.column(card) for card in cards], multiline=True)
