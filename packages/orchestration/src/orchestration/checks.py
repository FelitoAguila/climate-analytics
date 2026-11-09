"""Asset checks: quality tests that run after each update, with the read-only user.

They are blocking: if one fails, the run fails, so a scheduled run is marked in red.
"""

import os
from datetime import UTC, date, datetime

import dagster as dg

from orchestration.assets import daily_temperatures
from orchestration.resources import NeonResource

# ERA5 arrives about 7 days late; 10 leaves room for a day or two without updates.
# The MAX_DAYS_BEHIND environment variable changes it (for example, to test a failure).
MAX_DAYS_BEHIND = 10


def max_days_behind() -> int:
    return int(os.environ.get("MAX_DAYS_BEHIND", MAX_DAYS_BEHIND))


def days_behind(oldest_last_day: date, today: date) -> int:
    return (today - oldest_last_day).days


@dg.asset_check(asset=daily_temperatures, blocking=True)
def data_is_fresh(neon_reader: NeonResource) -> dg.AssetCheckResult:
    """Every city reaches at most MAX_DAYS_BEHIND days before today."""
    with neon_reader.connect() as connection:
        oldest, newest = connection.execute(
            """SELECT MIN(last_day), MAX(last_day)
               FROM (SELECT MAX(date) AS last_day FROM daily GROUP BY city_id) AS cities"""
        ).fetchone()
    behind = days_behind(oldest, datetime.now(UTC).date())
    limit = max_days_behind()
    return dg.AssetCheckResult(
        passed=behind <= limit,
        metadata={
            "oldest_last_day": str(oldest),
            "newest_last_day": str(newest),
            "days_behind": behind,
            "max_days_behind": limit,
        },
    )


@dg.asset_check(asset=daily_temperatures, blocking=True)
def no_missing_days(neon_reader: NeonResource) -> dg.AssetCheckResult:
    """Each city has every day between its first and its last date."""
    with neon_reader.connect() as connection:
        rows = connection.execute(
            """SELECT city_id, (MAX(date) - MIN(date) + 1) - COUNT(*) AS missing
               FROM daily GROUP BY city_id HAVING (MAX(date) - MIN(date) + 1) <> COUNT(*)"""
        ).fetchall()
    return dg.AssetCheckResult(
        passed=not rows,
        metadata={
            "cities_with_gaps": len(rows),
            "examples": ", ".join(f"{city} ({n} days)" for city, n in rows[:5])
            or "none",
        },
    )


@dg.asset_check(asset=daily_temperatures, blocking=True)
def temperatures_are_consistent(neon_reader: NeonResource) -> dg.AssetCheckResult:
    """No day has its minimum above its mean, or its mean above its maximum."""
    with neon_reader.connect() as connection:
        (wrong,) = connection.execute(
            "SELECT COUNT(*) FROM daily WHERE NOT (t_min <= t_mean AND t_mean <= t_max)"
        ).fetchone()
    return dg.AssetCheckResult(passed=wrong == 0, metadata={"wrong_days": wrong})
