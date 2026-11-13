"""Database engine, query execution and the small read cache."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from functools import wraps
from threading import Lock
from typing import Any, ParamSpec, TypeVar

import pandas as pd
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ArgumentError, SQLAlchemyError

from ..errors import ConfigurationError, DataUnavailable
from ..settings import database_url, get_settings

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

_engine_lock = Lock()
_engine: Engine | None = None

_caches_lock = Lock()
_caches: list[TTLCache] = []


def ttl_cache(
    seconds: float, maxsize: int = 128
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Cache a function's result for a number of seconds and return DataFrame copies."""

    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        cache: TTLCache = TTLCache(maxsize=maxsize, ttl=seconds)
        with _caches_lock:
            _caches.append(cache)

        cached_function = cached(cache=cache, key=hashkey, lock=Lock())(function)

        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = cached_function(*args, **kwargs)
            if isinstance(result, pd.DataFrame):
                return result.copy()
            return result

        wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
        return wrapper

    return decorator


def clear_data_caches() -> None:
    """Clear every query cache. Used after data changes and in tests."""
    with _caches_lock:
        for cache in _caches:
            cache.clear()


def get_engine() -> Engine:
    """Return the process-wide read-only engine, creating it on first use."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = _build_engine()
    return _engine


def reset_engine() -> None:
    """Dispose and forget the engine. Used on shutdown and in tests."""
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.dispose()
            _engine = None


def _build_engine() -> Engine:
    settings = get_settings()
    try:
        return create_engine(
            database_url(settings),
            pool_pre_ping=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=settings.db_pool_recycle_seconds,
            pool_timeout=settings.db_pool_timeout_seconds,
            connect_args={
                "application_name": "dash-app",
                "connect_timeout": settings.db_connect_timeout_seconds,
                "options": (
                    "-c default_transaction_read_only=on "
                    f"-c statement_timeout={settings.db_statement_timeout_ms}"
                ),
            },
        )
    except ArgumentError:
        raise ConfigurationError(
            "READONLY_DATABASE_URL is not a valid PostgreSQL connection string."
        ) from None


def fetch_df(
    sql: str,
    params: Mapping[str, Any] | None = None,
    *,
    parse_dates: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Run a read-only SQL query and return the rows as a DataFrame."""
    try:
        engine = get_engine()
        with engine.connect() as connection:
            return pd.read_sql_query(
                text(sql),
                connection,
                params=dict(params or {}),
                parse_dates=list(parse_dates) if parse_dates else None,
            )
    except ConfigurationError:
        raise
    except (SQLAlchemyError, pd.errors.DatabaseError) as error:
        logger.warning("Database query failed (%s)", type(error).__name__)
        raise DataUnavailable(
            "The climate database is unavailable. Please try again later."
        ) from error
