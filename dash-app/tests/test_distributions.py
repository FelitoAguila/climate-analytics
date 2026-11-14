"""Offline tests for annual temperature distributions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from dash_app.callbacks import city_map as city_map_callbacks
from dash_app.components import distributions
from dash_app.data import DataUnavailable


def _frame() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    frames = []
    for year, mean in ((1950, 10.0), (2000, 13.0)):
        dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
        values = rng.normal(mean, 2.0, len(dates))
        frames.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "t_mean": values,
                    "t_min": values - 5.0,
                    "t_max": values + 5.0,
                }
            )
        )

    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    values = rng.normal(15.0, 2.0, len(dates))
    frames.append(
        pd.DataFrame(
            {
                "date": dates,
                "t_mean": values,
                "t_min": values - 5.0,
                "t_max": values + 5.0,
            }
        )
    )
    return pd.concat(frames, ignore_index=True)


def test_build_distribution_figure_has_one_ridge_per_year():
    figure, years = distributions.build_distribution_figure(
        _frame(), "t_mean", 1940, 2026
    )

    assert years == [1950, 2000, 2026]
    ridge_lines = [trace for trace in figure.data if trace.fill != "toself"]
    fill_traces = [trace for trace in figure.data if trace.fill == "toself"]
    assert len(fill_traces) == 3
    assert [trace.name for trace in ridge_lines] == ["1950", "2000", "2026"]

    peaks = []
    for trace in ridge_lines:
        x_values = np.asarray(trace.x)
        y_values = np.asarray(trace.y)
        peaks.append(float(x_values[int(np.argmax(y_values))]))
        assert trace.showlegend is False

    np.testing.assert_allclose(peaks[0], 10.0, atol=1.0)
    np.testing.assert_allclose(peaks[1], 13.0, atol=1.0)
    np.testing.assert_allclose(peaks[2], 15.0, atol=1.0)
    assert figure.layout.xaxis.title.text == "Mean temperature (°C)"
    assert figure.layout.yaxis.title.text == "Year"


def test_build_distribution_figure_uses_selected_variable():
    figure, _ = distributions.build_distribution_figure(_frame(), "t_min", 1950, 2000)

    assert figure.layout.xaxis.title.text == "Minimum temperature (°C)"


def test_build_distribution_figure_handles_empty_range():
    figure, years = distributions.build_distribution_figure(
        _frame(), "t_mean", 1800, 1801
    )

    assert years == []
    assert len(figure.data) == 0
    assert "No data" in figure.layout.annotations[0].text


def test_distribution_theme_and_marks():
    light = distributions.distribution_theme("light")
    dark = distributions.distribution_theme("dark")
    marks = distributions.year_marks(1940, 2026)

    assert light != dark
    assert marks[1940] == "1940"
    assert marks[2020] == "2020"
    assert marks[2026] == "2026"

    figure, _ = distributions.build_distribution_figure(
        _frame(), "t_mean", 1950, 2026, theme="dark"
    )
    assert figure.layout.font.color == dark["text"]
    assert figure.layout.xaxis.gridcolor == dark["grid"]


def test_empty_distribution_figure():
    figure = distributions.empty_distribution_figure("dark", "Nothing here")

    assert figure.layout.annotations[0].text == "Nothing here"
    assert figure.layout.xaxis.visible is False
    assert figure.layout.height == 360


def test_available_years_includes_partial_years():
    assert city_map_callbacks._available_years(_frame()) == (1950, 2026)


def test_year_range_response(monkeypatch):
    monkeypatch.setattr(city_map_callbacks, "city_daily", lambda city_id: _frame())

    start, end, value, marks, disabled = city_map_callbacks.year_range_response(
        "phoenix-us"
    )

    assert (start, end) == (1950, 2026)
    assert value == [1950, 2026]
    assert marks == distributions.year_marks(1950, 2026)
    assert disabled is False


def test_year_range_response_without_city():
    _, _, _, _, disabled = city_map_callbacks.year_range_response(None)

    assert disabled is True


def test_distribution_response(monkeypatch):
    monkeypatch.setattr(city_map_callbacks, "city_daily", lambda city_id: _frame())
    monkeypatch.setattr(
        city_map_callbacks,
        "get_city",
        lambda city_id: {"name": "Phoenix", "country": "United States"},
    )

    figure, title, status = city_map_callbacks.distribution_response(
        "phoenix-us", "t_mean", [1950, 2026], "light"
    )

    assert title == "Phoenix (United States)"
    assert status == "Mean temperature · 1950–2026 · 3 years"
    assert len([trace for trace in figure.data if trace.fill != "toself"]) == 3


def test_distribution_response_without_city():
    figure, title, status = city_map_callbacks.distribution_response(
        None, "t_mean", None, "dark"
    )

    assert title == "Select a city"
    assert "Choose a city" in status
    assert len(figure.data) == 0


def test_distribution_response_handles_unavailable_data(monkeypatch):
    def fail(city_id):
        raise DataUnavailable("unavailable")

    monkeypatch.setattr(city_map_callbacks, "city_daily", fail)
    monkeypatch.setattr(
        city_map_callbacks,
        "get_city",
        lambda city_id: {"name": "Phoenix", "country": "United States"},
    )

    _, title, status = city_map_callbacks.distribution_response(
        "phoenix-us", "t_mean", [1950, 2026], "light"
    )

    assert title == "Phoenix (United States)"
    assert "could not be loaded" in status
