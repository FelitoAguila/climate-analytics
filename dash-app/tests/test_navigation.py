"""Smoke tests for routing, the page registry and app bootstrap."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest
from dash_app import config
from dash_app.app import create_app
from dash_app.data import DataUnavailable
from dash_app.pages import about, features, home, registry
from dash_app.utils import is_active


@pytest.fixture(scope="module")
def app():
    return create_app()


def test_normalize():
    assert registry.normalize(None) == "/"
    assert registry.normalize("") == "/"
    assert registry.normalize("/about/") == "/about"
    assert registry.normalize("/about?from=home") == "/about"


def test_resolve_static_pages():
    home = registry.resolve("/")
    assert home.found
    assert home.nav_key == "/"
    assert home.layout is not None

    about_page = registry.resolve("/about")
    assert about_page.found
    assert about_page.nav_key == "/about"

    features_page = registry.resolve("/features")
    assert features_page.found
    assert features_page.nav_key == "/features"


def test_browse_page_is_removed():
    assert registry.resolve("/browse").found is False
    assert registry.resolve("/browse/record-001").found is False


def test_resolve_not_found():
    resolved = registry.resolve("/does-not-exist")
    assert resolved.found is False
    assert resolved.nav_key is None
    assert resolved.layout is not None


def test_home_overview_uses_database_status(monkeypatch):
    fake_status = SimpleNamespace(
        city_count=140,
        row_count=4_440_945,
        first_date=date(1940, 1, 1),
        latest_date=date(2026, 11, 6),
        cities=pd.DataFrame({"complete": [True] * 140}),
    )
    monkeypatch.setattr(home, "data_status", lambda: fake_status)

    payload = str(home.layout().to_plotly_json())

    assert "140" in payload
    assert "4,440,945" in payload
    assert "87" in payload
    assert "1940–2026" in payload
    assert "6 Nov 2026" in payload


def test_home_overview_handles_database_error(monkeypatch):
    def fail():
        raise DataUnavailable("unavailable")

    monkeypatch.setattr(home, "data_status", fail)

    payload = str(home.layout().to_plotly_json())
    assert "Live data unavailable" in payload


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
    assert not is_active("/", "/features")
    assert is_active("/features", "/features")
    assert not is_active("/features", "/about")
    assert not is_active("https://example.com", "/")


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


def test_about_menu_has_no_placeholder_links():
    labels = {item.label for item in config.ABOUT_MENU}
    hrefs = {item.href for item in config.ABOUT_MENU}

    assert "Documentation" not in labels
    assert "Contact" not in labels
    assert config.GITHUB_REPO_URL in hrefs
    assert "/about#authors" in hrefs
    assert not any("dash.plotly.com" in href for href in hrefs)
    assert not any("feedback@example.com" in href for href in hrefs)


def test_footer_and_about_menu_share_project_links():
    about_hrefs = {item.href for item in config.ABOUT_MENU}
    footer_hrefs = {item.href for item in config.FOOTER_LINKS}

    assert {"/about", "/about#authors", config.GITHUB_REPO_URL} <= about_hrefs
    assert {"/", "/about", "/about#authors", config.GITHUB_REPO_URL} <= footer_hrefs
    assert "/browse" not in footer_hrefs
    assert config.OPEN_METEO_URL in footer_hrefs


def test_authors_have_project_links():
    assert len(config.AUTHORS) == 2
    for author in config.AUTHORS:
        labels = {link.label for link in author.links}
        assert {"GitHub", "LinkedIn", "Website"} <= labels
        for link in author.links:
            assert link.external
            assert link.href.startswith("https://")


def test_about_authors_layout():
    classes: list[str] = []
    ids: set[str] = set()
    _walk(about.layout(), classes, ids)
    payload = str(about.layout().to_plotly_json())

    assert "authors" in ids
    assert "mp-author-card" in classes
    assert "mp-author-link" in classes
    assert classes.count("mp-author-card") == len(config.AUTHORS)
    for author in config.AUTHORS:
        assert author.name in payload
