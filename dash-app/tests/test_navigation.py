"""Smoke tests for routing, the page registry and app bootstrap."""

from __future__ import annotations

import pytest

from dash_app.app import create_app
from dash_app.callbacks.search import apply_filters, build_search_href
from dash_app.data import placeholder
from dash_app.pages import registry
from dash_app.pages import features
from dash_app.utils import is_active


@pytest.fixture(scope="module")
def app():
    return create_app()


def test_normalize():
    assert registry.normalize(None) == "/"
    assert registry.normalize("") == "/"
    assert registry.normalize("/browse/") == "/browse"
    assert registry.normalize("/browse?q=test") == "/browse"
    assert registry.normalize("/about/") == "/about"


def test_resolve_static_pages():
    home = registry.resolve("/")
    assert home.found
    assert home.nav_key == "/"
    assert home.layout is not None

    browse = registry.resolve("/browse")
    assert browse.found
    assert browse.nav_key == "/browse"


def test_resolve_dynamic_route():
    resolved = registry.resolve("/browse/record-001")
    assert resolved.found
    assert resolved.nav_key == "/browse"


def test_resolve_not_found():
    resolved = registry.resolve("/does-not-exist")
    assert resolved.found is False
    assert resolved.nav_key is None
    assert resolved.layout is not None


def test_placeholder_data():
    frame = placeholder.records()
    assert not frame.empty
    assert {"id", "name", "category", "status", "score", "updated"} <= set(frame.columns)
    assert placeholder.get_record("record-001") is not None
    assert placeholder.get_record("nope") is None


def test_app_layout_and_callbacks(app):
    assert app.layout is not None
    assert len(app.callback_map) >= 5


def test_index_serves(app):
    client = app.server.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"react-entry-point" in response.data

    layout = client.get("/_dash-layout")
    assert layout.status_code == 200
    assert b"mp-app" in layout.data


def test_is_active():
    assert is_active("/", "/")
    assert not is_active("/", "/browse")
    assert is_active("/browse", "/browse")
    assert is_active("/browse", "/browse/record-001")
    assert not is_active("/browse", "/about")
    assert not is_active("https://example.com", "/")


def test_apply_filters():
    frame = placeholder.records()
    filtered = apply_filters(frame, text="Aurora")
    assert len(filtered) == 1
    assert filtered.iloc[0]["name"] == "Aurora"

    by_category = apply_filters(frame, category="Alpha")
    assert not by_category.empty
    assert (by_category["category"] == "Alpha").all()

    by_status = apply_filters(frame, status="Active")
    assert (by_status["status"] == "Active").all()

    ascending = apply_filters(frame, sort_key="score_asc")
    assert ascending["score"].is_monotonic_increasing

    descending = apply_filters(frame, sort_key="score_desc")
    assert descending["score"].is_monotonic_decreasing


def test_build_search_href():
    assert build_search_href("Aurora") == "/browse?q=Aurora"
    assert build_search_href("  spaced term ") == "/browse?q=spaced%20term"
    assert build_search_href("") is None
    assert build_search_href(None) is None


def _walk(node, classes, ids):
    if isinstance(node, (list, tuple)):
        for item in node:
            _walk(item, classes, ids)
        return
    if isinstance(node, dict):
        props = node.get("props", {})
    elif hasattr(node, "to_plotly_json"):
        props = node.to_plotly_json().get("props", {})
    else:
        return
    class_name = props.get("className")
    if class_name:
        classes.extend(class_name.split())
    if props.get("id"):
        ids.add(props["id"])
    _walk(props.get("children"), classes, ids)


def test_features_dashboard_layout():
    classes: list[str] = []
    ids: set[str] = set()
    _walk(features.layout(), classes, ids)

    assert "mp-dashboard" in classes
    assert "mp-dashboard-main" in classes
    assert "mp-page-header" in classes
    assert "mp-feature-grid" in classes
    assert "mp-sidenav" in classes and "mp-sidenav" in ids
    assert "mp-sidenav-toggle" in ids
    assert classes.count("mp-dash-card") == 8


def test_sidenav_callback_registered(app):
    assert any("mp-sidenav" in key for key in app.callback_map)

