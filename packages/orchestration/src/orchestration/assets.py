"""Assets: the data Dagster keeps up to date."""

from datetime import UTC, datetime

import dagster as dg
from pipelines.update import read_cities, update

from orchestration.resources import NeonResource


@dg.asset(kinds={"postgres"})
def daily_temperatures(
    context: dg.AssetExecutionContext, neon_writer: NeonResource
) -> dg.MaterializeResult:
    """Daily temperatures of every city in Neon (table `daily`), from 1940 until about a week ago.

    Materializing it asks the API for the newest days of each city and writes the new or
    corrected ones (the same as `uv run update-neon`).
    """
    with neon_writer.connect() as connection:
        cities = read_cities(connection)
        summary = update(connection, cities, datetime.now(UTC).date(), context.log.info)

    metadata = {
        "new_days": summary.new_days,
        "changed_days": summary.changed_days,
        "largest_change_celsius": round(summary.largest_change, 2),
        "api_calls": round(summary.api_calls),
        "cities": len(cities),
        "complete_until": str(summary.complete_until),
    }
    if summary.failed:
        # The run ends in error: the cities that did work are already saved
        raise dg.Failure(
            description=f"Could not update: {', '.join(summary.failed)}",
            metadata={**metadata, "failed": ", ".join(summary.failed)},
        )
    return dg.MaterializeResult(metadata=metadata)
