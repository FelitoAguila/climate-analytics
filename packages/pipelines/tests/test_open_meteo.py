import pandas as pd
import pytest
from pipelines.open_meteo import build_params, grid_cell, request_cost, to_dataframe


def test_cost_of_a_full_city():
    # 1940-01-01 to 2025-12-31 is 31,412 days: 0.3 × 31,412 / 14
    assert request_cost(31_412) == pytest.approx(673.1, abs=0.05)


def test_cost_is_never_below_one_call():
    assert request_cost(7) == 1.0


def test_cost_grows_with_variables_and_models():
    assert request_cost(365, n_variables=1) == pytest.approx(365 / 14 / 10)
    assert request_cost(365, n_models=2) == pytest.approx(2 * request_cost(365))


def test_params_ask_for_era5_by_default():
    params = build_params(40.4, -3.7, "2024-07-01", "2024-07-07")
    assert params["models"] == "era5"
    assert params["timezone"] == "GMT"
    assert (
        params["daily"] == "temperature_2m_mean,temperature_2m_max,temperature_2m_min"
    )


def test_params_without_model_use_the_api_default():
    assert "models" not in build_params(
        40.4, -3.7, "2024-07-01", "2024-07-07", model=None
    )


PAYLOAD = {
    "latitude": 40.5,
    "longitude": -3.75,
    "elevation": 616.0,
    "daily": {
        "time": ["2024-07-01", "2024-07-02"],
        "temperature_2m_mean": [25.1, 26.3],
        "temperature_2m_max": [33.0, 34.2],
        "temperature_2m_min": [17.4, 18.0],
    },
}


def test_to_dataframe_renames_and_parses_dates():
    daily = to_dataframe(PAYLOAD)
    assert list(daily.columns) == ["date", "t_mean", "t_max", "t_min"]
    assert daily["date"].iloc[0] == pd.Timestamp("2024-07-01")
    assert daily["t_max"].tolist() == [33.0, 34.2]


def test_grid_cell():
    assert grid_cell(PAYLOAD) == {
        "latitude": 40.5,
        "longitude": -3.75,
        "elevation": 616.0,
    }
