"""Bulma primitives.

Thin helpers that attach the right Bulma class names so pages never need to
write raw class strings. Modelled on ``crystal_toolkit.helpers.layouts``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from dash import dcc, html

BulmaColor = Literal[
    "white",
    "black",
    "light",
    "dark",
    "primary",
    "link",
    "info",
    "success",
    "warning",
    "danger",
]

ColorArg = BulmaColor | None


def _merge_class(
    kwargs: dict[str, Any], class_name: str, condition: bool = True
) -> None:
    if not condition:
        return
    existing = kwargs.get("className")
    kwargs["className"] = f"{existing} {class_name}" if existing else class_name


def container(children: Any = None, fluid: bool = False, **kwargs) -> html.Div:
    _merge_class(kwargs, "container")
    _merge_class(kwargs, "is-fluid", fluid)
    return html.Div(children, **kwargs)


def box(children: Any = None, **kwargs) -> html.Div:
    _merge_class(kwargs, "box")
    return html.Div(children, **kwargs)


def section(children: Any = None, **kwargs) -> html.Section:
    _merge_class(kwargs, "section")
    return html.Section(children, **kwargs)


def columns(
    children: Any = None,
    *,
    centered: bool = False,
    gapless: bool = False,
    multiline: bool = False,
    **kwargs,
) -> html.Div:
    _merge_class(kwargs, "columns")
    _merge_class(kwargs, "is-centered", centered)
    _merge_class(kwargs, "is-gapless", gapless)
    _merge_class(kwargs, "is-multiline", multiline)
    return html.Div(children, **kwargs)


def column(
    children: Any = None, *, size: str | int | None = None, **kwargs
) -> html.Div:
    _merge_class(kwargs, "column")
    _merge_class(kwargs, f"is-{size}", size is not None)
    return html.Div(children, **kwargs)


def title(
    text: Any, *, size: int = 1, spaced: bool = False, subtitle: bool = False, **kwargs
) -> html.H1:
    _merge_class(kwargs, "title" if not subtitle else "subtitle")
    _merge_class(kwargs, f"is-{size}")
    _merge_class(kwargs, "is-spaced", spaced)
    return html.H1(text, **kwargs)


def subtitle(text: Any, *, size: int = 5, **kwargs) -> html.H2:
    return title(text, size=size, subtitle=True, **kwargs)


def hero(
    children: Any = None,
    *,
    color: ColorArg = None,
    size: str | None = None,
    **kwargs,
) -> html.Section:
    _merge_class(kwargs, "hero")
    _merge_class(kwargs, f"is-{color}", color is not None)
    _merge_class(kwargs, f"is-{size}", size is not None)
    return html.Section(children, **kwargs)


def hero_body(children: Any = None, **kwargs) -> html.Div:
    _merge_class(kwargs, "hero-body")
    return html.Div(children, **kwargs)


def card(children: Any = None, **kwargs) -> html.Div:
    _merge_class(kwargs, "card")
    return html.Div(children, **kwargs)


def card_header(children: Any = None, **kwargs) -> html.Header:
    _merge_class(kwargs, "card-header")
    return html.Header(children, **kwargs)


def card_header_title(text: Any, **kwargs) -> html.P:
    _merge_class(kwargs, "card-header-title")
    return html.P(text, **kwargs)


def card_content(children: Any = None, **kwargs) -> html.Div:
    _merge_class(kwargs, "card-content")
    return html.Div(children, **kwargs)


def card_footer(children: Any = None, **kwargs) -> html.Footer:
    _merge_class(kwargs, "card-footer")
    return html.Footer(children, **kwargs)


def card_footer_item(children: Any = None, **kwargs) -> html.A:
    _merge_class(kwargs, "card-footer-item")
    return html.A(children, **kwargs)


def notification(
    children: Any = None, *, color: ColorArg = None, light: bool = False, **kwargs
) -> html.Div:
    _merge_class(kwargs, "notification")
    _merge_class(kwargs, f"is-{color}", color is not None)
    _merge_class(kwargs, "is-light", light)
    return html.Div(children, **kwargs)


def message(
    children: Any = None,
    *,
    color: ColorArg = "info",
    header: str | None = None,
    **kwargs,
) -> html.Article:
    _merge_class(kwargs, "message")
    _merge_class(kwargs, f"is-{color}", color is not None)
    content = []
    if header:
        content.append(html.Div(header, className="message-header"))
    content.append(html.Div(children, className="message-body"))
    return html.Article(content, **kwargs)


def tag(
    text: Any,
    *,
    color: ColorArg = "primary",
    rounded: bool = False,
    light: bool = False,
    **kwargs,
) -> html.Span:
    _merge_class(kwargs, "tag")
    _merge_class(kwargs, f"is-{color}", color is not None)
    _merge_class(kwargs, "is-rounded", rounded)
    _merge_class(kwargs, "is-light", light)
    return html.Span(text, **kwargs)


def tags(children: Sequence[Any], **kwargs) -> html.Div:
    _merge_class(kwargs, "tags")
    return html.Div(list(children), **kwargs)


def level(children: Any = None, *, mobile: bool = False, **kwargs) -> html.Nav:
    _merge_class(kwargs, "level")
    _merge_class(kwargs, "is-mobile", mobile)
    return html.Nav(children, **kwargs)


def level_left(children: Any = None, **kwargs) -> html.Div:
    _merge_class(kwargs, "level-left")
    return html.Div(children, **kwargs)


def level_right(children: Any = None, **kwargs) -> html.Div:
    _merge_class(kwargs, "level-right")
    return html.Div(children, **kwargs)


def level_item(children: Any = None, *, centered: bool = False, **kwargs) -> html.Div:
    _merge_class(kwargs, "level-item")
    _merge_class(kwargs, "has-text-centered", centered)
    return html.Div(children, **kwargs)


def button(
    children: Any = None,
    *,
    color: ColorArg = "primary",
    light: bool = False,
    rounded: bool = False,
    outlined: bool = False,
    href: str | None = None,
    **kwargs,
) -> Any:
    _merge_class(kwargs, "button")
    _merge_class(kwargs, f"is-{color}", color is not None)
    _merge_class(kwargs, "is-light", light)
    _merge_class(kwargs, "is-rounded", rounded)
    _merge_class(kwargs, "is-outlined", outlined)
    if href is not None:
        return dcc.Link(children, href=href, **kwargs)
    return html.Button(children, **kwargs)


def breadcrumb(parts: Sequence[tuple[str, str]], **kwargs) -> html.Nav:
    _merge_class(kwargs, "breadcrumb")
    items = [
        html.Li(
            dcc.Link(name, href=href),
            className="is-active" if index == len(parts) - 1 else None,
        )
        for index, (name, href) in enumerate(parts)
    ]
    return html.Nav(html.Ul(items), **kwargs)


def menu(children: Any = None, **kwargs) -> html.Div:
    _merge_class(kwargs, "menu")
    return html.Div(children, **kwargs)


def menu_label(text: Any, **kwargs) -> html.P:
    _merge_class(kwargs, "menu-label")
    return html.P(text, **kwargs)


def menu_list(children: Any = None, **kwargs) -> html.Ul:
    _merge_class(kwargs, "menu-list")
    return html.Ul(children, **kwargs)


def menu_item(
    children: Any = None, *, active: bool = False, href: str | None = None, **kwargs
) -> html.Li:
    _merge_class(kwargs, "is-active", active)
    if href is not None:
        return html.Li(dcc.Link(children, href=href), **kwargs)
    return html.Li(children, **kwargs)


def icon(name: str, **kwargs) -> html.Span:
    return html.Span(html.I(className=name), className="icon", **kwargs)


def heading(
    text: Any, *, size: int = 1, subtitle: bool = False, spaced: bool = False, **kwargs
) -> Any:
    tag_name = f"h{min(max(size, 1), 6)}"
    _merge_class(kwargs, "title" if not subtitle else "subtitle")
    _merge_class(kwargs, f"is-{size}")
    _merge_class(kwargs, "is-spaced", spaced)
    return html.__dict__[tag_name.capitalize()](text, **kwargs)
