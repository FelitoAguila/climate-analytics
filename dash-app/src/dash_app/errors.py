"""Exceptions shared by the application and the data layer."""

from __future__ import annotations


class DataLayerError(Exception):
    """Base class for errors raised while reading climate data."""


class ConfigurationError(DataLayerError):
    """The database configuration is missing or invalid."""


class DataUnavailable(DataLayerError):
    """The database could not be reached or a query failed."""
