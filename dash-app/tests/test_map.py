"""Offline tests for the city map feature."""

from __future__ import annotations

import pandas as pd

from dash_app.components import maps
from dash_app.data import DataUnavailable
from dash_app.pages import city_map


def _cities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "phoenix-us",
                "name": "Phoenix",
                "country": "United States",
                "country_code": "US",
                "continent": "North America",
                "latitude": 33.5419,
                "longitude": -112.0719,
                "population": 3_551_000,
                "is_capital": False,
                "coastal": False,
            },
            {
                "id": "paris-fr",
                "name": "Paris",
                "country": "France",
                "country_code": "FR",
                "continent": "Europe",
                "latitude": 48.8566,
                "longitude": 2.3522,
                "population": 2_100_000,
                "is_capital": True,
                "coastal": False,
            },
            {
                "id": "sydney-au",
                "name": "Sydney",
                "country": "Australia",
                "country_code": "AU",
                "continent": "Oceania",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "population": 5_300_000,
                "is_capital": False,
                "coastal": True,
            },
        ]
    )


def _walk(node, ids: set[str]) -> None:
    if isinstance(node, (list, tuple)):
        for item in node:
            _walk(item, ids)
        return
    if isinstance(node, dict):
        props = node.get("props", {})
    elif hasattr(node, "to_plotly_json"):
        props = node.to_plotly_json().get("props", {})
    else:
        return
    if props.get("id"):
        ids.add(props["id"])
    _walk(props.get("children"), ids)


def test_build_city_map_traces_and_hover():
    figure = maps.build_city_map(_cities())

    assert len(figure.data) == 3
    assert {trace.name for trace in figure.data} == {
        "Europe",
        "North America",
        "Oceania",
    }
    assert sum(len(trace.lat) for trace in figure.data) == 3

    hover = [text for trace in figure.data for text in trace.hovertext]
    assert any("Phoenix" in text for text in hover)
    assert any("United States" in text for text in hover)
    assert any("North America" in text for text in hover)
    assert not any("Population" in text for text in hover)
    assert not any("Capital" in text or "Coastal" in text for text in hover)

    sizes = [trace.marker.size for trace in figure.data]
    assert sizes == [maps._MARKER_SIZE] * len(figure.data)
    assert {trace.text[0] for trace in figure.data} == {
        "Phoenix",
        "Paris",
        "Sydney",
    }
    assert {trace.customdata[0] for trace in figure.data} == {
        "phoenix-us",
        "paris-fr",
        "sydney-au",
    }
    assert figure.layout.geo.projection.type == "natural earth"
    assert figure.layout.geo.landcolor == maps.map_colors("light")["land"]


def test_map_theme_patch_updates_geo_colours():
    dark = maps.map_colors("dark")
    operations = {
        tuple(operation["location"]): operation["params"]["value"]
        for operation in maps.map_theme_patch("dark").to_plotly_json()["operations"]
    }

    assert dark != maps.map_colors("light")
    assert operations[("layout", "geo", "landcolor")] == dark["land"]
    assert operations[("layout", "geo", "oceancolor")] == dark["ocean"]
    assert operations[("layout", "legend", "font", "color")] == dark["text"]
    assert operations[("layout", "hoverlabel", "bgcolor")] == dark["hover_bg"]


def test_city_map_layout(monkeypatch):
    monkeypatch.setattr(city_map, "list_cities", _cities)

    layout = city_map.layout()
    ids: set[str] = set()
    _walk(layout, ids)
    payload = str(layout.to_plotly_json())

    assert maps.MAP_ID in ids
    assert {
        "city-filter",
        "distribution-chart",
        "distribution-city",
        "temperature-variable",
        "year-range",
    } <= ids
    assert "World map" in payload
    assert "Annual temperature distributions" in payload
    assert "Every city on one map" in payload
    assert "Continents" in payload
    assert "Countries" in payload
    assert "Phoenix" in payload
    assert "Phoenix (US)" in payload
    assert "Scroll to zoom" in payload
    assert "Use the city filter below" in payload


def test_city_map_layout_handles_unavailable_data(monkeypatch):
    def fail():
        raise DataUnavailable("unavailable")

    monkeypatch.setattr(city_map, "list_cities", fail)

    payload = str(city_map.layout().to_plotly_json())

    assert "Map unavailable" in payload
    assert "city-map" not in payload


def test_city_map_empty_dataset(monkeypatch):
    monkeypatch.setattr(city_map, "list_cities", pd.DataFrame)

    payload = str(city_map.layout().to_plotly_json())

    assert "Map unavailable" in payload
