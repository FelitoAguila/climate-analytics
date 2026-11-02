import matplotlib
import numpy as np
import pandas as pd
import pytest
from analysis.bells import (
    curves_per_year,
    days_per_degree,
    decade_label,
    decade_means,
    silverman_bandwidth,
    temperature_axis,
)
from analysis.plots import plot_bells, plot_bells_comparison, plot_decade_bells

matplotlib.use("Agg")  # no window in the tests

rng = np.random.default_rng(seed=42)


def city_daily(first_year=1940, last_year=1959, warming_per_year=0.1):
    """A city with normal daily temperatures (sd 3 °C) whose mean rises every year."""
    dates = pd.date_range(f"{first_year}-01-01", f"{last_year}-12-31", freq="D")
    t_mean = (
        15 + warming_per_year * (dates.year - first_year) + rng.normal(0, 3, len(dates))
    )
    return pd.DataFrame(
        {
            "city_id": "test-xx",
            "date": dates,
            "year": dates.year,
            "t_mean": t_mean,
            "t_max": t_mean + 5,
            "t_min": t_mean - 5,
        }
    )


def test_silverman_bandwidth_of_a_normal_sample():
    values = rng.normal(0, 3, 100_000)
    assert silverman_bandwidth(values) == pytest.approx(0.9 * 3 * 365**-0.2, rel=0.02)


def test_area_under_a_year_is_its_number_of_days():
    values = rng.normal(15, 3, 365)
    axis = np.linspace(-5, 35, 400)
    curve = days_per_degree(values, axis, h=1.0)
    assert np.trapezoid(curve, axis) == pytest.approx(365, rel=1e-3)


def test_warming_moves_the_bells_to_the_right():
    daily = city_daily()
    axis = temperature_axis(daily)
    _, curves = curves_per_year(daily, "t_mean", axis)
    decades = decade_means(curves)
    assert list(decades) == [1940, 1950]
    peak = {decade: axis[np.argmax(curve)] for decade, curve in decades.items()}
    # +0.1 °C a year: the 1950s are about 1 °C warmer than the 1940s
    assert peak[1950] - peak[1940] == pytest.approx(1.0, abs=0.5)


def test_temperature_axis_covers_minima_and_maxima():
    daily = city_daily()
    axis = temperature_axis(daily, points=50)
    assert len(axis) == 50
    assert axis[0] < daily["t_min"].min() and axis[-1] > daily["t_max"].max()


def test_no_bell_is_cut_at_the_edges():
    # Days spread evenly up to the extremes: many of them sit at the edge of the axis, so a
    # plain 5 % margin (0.5 °C here, less than one bell width) would cut their tails
    dates = pd.date_range("2001-01-01", "2003-12-31", freq="D")
    t = rng.uniform(0, 10, len(dates))
    daily = pd.DataFrame(
        {"date": dates, "year": dates.year, "t_mean": t, "t_max": t, "t_min": t}
    )
    axis = temperature_axis(daily, points=600)
    _, curves = curves_per_year(daily, "t_mean", axis)
    for curve in curves.values():
        assert np.trapezoid(curve, axis) == pytest.approx(365, abs=0.5)


def test_decade_label():
    assert decade_label(1940, 2025) == "1940–1949"
    assert decade_label(2020, 2025) == "2020–2025"


def test_bell_charts():
    daily = city_daily()
    fig = plot_bells(daily, "test-xx")
    assert len(fig.axes) == 4  # three panels and the colour bar
    assert (
        len(fig.axes[0].lines) == 20 + 2 * 2 + 2
    )  # years, decades (with border), legend
    assert len(plot_decade_bells(daily, "test-xx").axes) == 3
    comparison = plot_bells_comparison(daily, ["test-xx"], variable="t_max")
    assert sum(ax.get_visible() for ax in comparison.axes) == 1
