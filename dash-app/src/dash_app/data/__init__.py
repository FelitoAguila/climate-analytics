"""Public read-only data API for the climate app."""

from __future__ import annotations

from ..errors import ConfigurationError, DataLayerError, DataUnavailable
from .db import clear_data_caches, fetch_df, reset_engine, ttl_cache
from .queries import (
    LESS_RELIABLE_BEFORE,
    RECENT_TREND_FROM,
    RECENT_YEARS,
    REFERENCE_PERIOD,
    DatasetStatus,
    city_annual_stats,
    city_daily,
    city_summaries,
    data_status,
    get_city,
    list_cities,
)

__all__ = [
    "LESS_RELIABLE_BEFORE",
    "RECENT_TREND_FROM",
    "RECENT_YEARS",
    "REFERENCE_PERIOD",
    "ConfigurationError",
    "DataLayerError",
    "DataUnavailable",
    "DatasetStatus",
    "city_annual_stats",
    "city_daily",
    "city_summaries",
    "clear_data_caches",
    "data_status",
    "fetch_df",
    "get_city",
    "list_cities",
    "reset_engine",
    "ttl_cache",
]
