import matplotlib
import numpy as np
import pandas as pd
import pytest
from analysis.plots import plot_annual_means
from analysis.stats import (
    annual_stats,
    city_summary,
    complete_years,
    read_database,
    trend_per_decade,
)

matplotlib.use("Agg")  # no window in the tests


def test_missing_database_says_what_to_do(tmp_path):
    with pytest.raises(FileNotFoundError, match="03_download"):
        read_database(tmp_path / "climate.db")
    # SQLite would otherwise create an empty file in read-write mode; nothing is created
    assert not (tmp_path / "climate.db").exists()


def synthetic_daily(first_year=1940, last_year=2025, warming_per_year=0.01):
    """One city whose temperature rises exactly `warming_per_year` °C every year."""
    dates = pd.date_range(f"{first_year}-01-01", f"{last_year}-12-31", freq="D")
    base = 15 + warming_per_year * (dates.year - first_year)
    return pd.DataFrame(
        {
            "city_id": "test-xx",
            "date": dates,
            "t_mean": base,
            "t_max": base + 5,
            "t_min": base - 5,
            "year": dates.year,
        }
    )


def test_complete_years_drops_partial_and_out_of_period_years():
    daily = synthetic_daily(2020, 2024)
    daily = daily[daily["date"] != "2021-06-01"]  # 2021 loses a day
    kept, dropped = complete_years(daily, 2020, 2023)
    assert sorted(kept["year"].unique()) == [2020, 2022, 2023]
    assert dropped[["year", "days", "expected"]].values.tolist() == [
        [2021, 364, 365],
        [2024, 366, 366],
    ]


def test_annual_stats_and_anomaly():
    annual = annual_stats(synthetic_daily())
    phoenix_like = annual.loc["test-xx"]
    assert phoenix_like.loc[1940, "mean"] == pytest.approx(15.0)
    assert phoenix_like.loc[1940, "max_mean"] == pytest.approx(20.0)
    assert phoenix_like.loc[1940, "p95"] == pytest.approx(15.0)  # every day is the same
    # The reference period is centred on 1975.5: its anomaly averages to zero
    assert phoenix_like.loc[1961:1990, "anomaly"].mean() == pytest.approx(0.0, abs=1e-9)


def test_trend_per_decade():
    assert trend_per_decade([2000, 2001, 2002], [10.0, 10.1, 10.2]) == pytest.approx(
        1.0
    )


def test_city_summary():
    summary = city_summary(annual_stats(synthetic_daily())).loc["test-xx"]
    assert summary["trend_decade"] == pytest.approx(0.1)
    assert summary["recent_trend"] == pytest.approx(0.1)
    # 2016–2025 (centre 2020.5) minus 1961–1990 (centre 1975.5): 45 years × 0.01 °C
    assert summary["difference"] == pytest.approx(0.45)
    assert summary["warmest_year"] == 2025
    assert (summary["first_year"], summary["last_year"]) == (1940, 2025)


def test_plot_annual_means_draws_three_lines_and_the_trend():
    annual = annual_stats(synthetic_daily())
    fig = plot_annual_means(annual, city_summary(annual), "test-xx", title="Test")
    assert len(fig.axes[0].lines) == 4
    assert np.isclose(fig.axes[0].lines[1].get_ydata()[0], 15.0)
