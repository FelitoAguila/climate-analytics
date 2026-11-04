"""Client for the Open-Meteo Historical Weather API (ERA5 reanalysis, from 1940).

The API is free and needs no key. Two things to keep in mind:

- It returns the nearest ERA5 grid cell (0.25°, ~25 km), not the exact point requested.
  `grid_cell` reads the cell that was actually used.
- A request over many days counts as several "calls" against the rate limits
  (see `request_cost`). One city from 1940 to today costs ~673 calls.

Retries and rate-limit handling live in the download pipeline, not here: `fetch_daily`
makes exactly one request.
"""

from datetime import date

import pandas as pd
import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# API variable name -> column name used in this project
DAILY_VARIABLES = {
    "temperature_2m_mean": "t_mean",
    "temperature_2m_max": "t_max",
    "temperature_2m_min": "t_min",
}

# Always ask for ERA5: the default model ("best_match") mixes sources of different resolution,
# which could look like a climate change when the source changes.
DEFAULT_MODEL = "era5"
FIRST_DATE = date(1940, 1, 1)

# Free tier limits, in calls
RATE_LIMITS = {"minute": 600, "hour": 5_000, "day": 10_000, "month": 300_000}


def request_cost(
    n_days: int, n_variables: int = len(DAILY_VARIABLES), n_models: int = 1
) -> float:
    """Calls a request costs for one location.

    Same formula as `calculateQueryWeight` in the Open-Meteo source code
    (Sources/App/Helper/Writer/ForecastApiResult.swift): 3 variables count as 0.3, and the
    cost grows linearly with the number of days, so splitting a request saves nothing.
    """
    variables_fraction = n_variables * n_models / 10
    days_fraction = n_days / 14
    return max(1.0, variables_fraction, variables_fraction * days_fraction)


def build_params(
    latitude: float,
    longitude: float,
    start: date | str,
    end: date | str,
    model: str | None = DEFAULT_MODEL,
) -> dict:
    """Query parameters for a daily request. `model=None` uses the API default (best_match)."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": str(start),
        "end_date": str(end),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "GMT",  # required for daily data: defines when each day starts
    }
    if model:
        params["models"] = model
    return params


def fetch_daily(
    latitude: float,
    longitude: float,
    start: date | str,
    end: date | str,
    model: str | None = DEFAULT_MODEL,
    timeout: float = 120,
) -> dict:
    """One request to the API. Returns the JSON as a dict; raises `requests.HTTPError` on errors."""
    response = requests.get(
        ARCHIVE_URL,
        params=build_params(latitude, longitude, start, end, model),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def to_dataframe(payload: dict) -> pd.DataFrame:
    """Daily values of a response as a DataFrame with columns date, t_mean, t_max, t_min."""
    daily = pd.DataFrame(payload["daily"])
    daily["time"] = pd.to_datetime(daily["time"])
    return daily.rename(columns={"time": "date", **DAILY_VARIABLES})[
        ["date", *DAILY_VARIABLES.values()]
    ]


def grid_cell(payload: dict) -> dict:
    """ERA5 cell the API actually used: latitude, longitude and elevation (m)."""
    return {key: payload[key] for key in ("latitude", "longitude", "elevation")}
