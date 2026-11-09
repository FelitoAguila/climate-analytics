"""Everything Dagster knows about this project. `uv run dagster dev` opens it in the browser."""

import dagster as dg

from orchestration.assets import daily_temperatures
from orchestration.checks import (
    data_is_fresh,
    no_missing_days,
    temperatures_are_consistent,
)
from orchestration.resources import neon_reader, neon_writer

# The job GitHub Actions runs every day: the update and its three checks
daily_update = dg.define_asset_job(
    "daily_update", selection=dg.AssetSelection.assets(daily_temperatures)
)

defs = dg.Definitions(
    jobs=[daily_update],
    assets=[daily_temperatures],
    asset_checks=[data_is_fresh, no_missing_days, temperatures_are_consistent],
    resources={"neon_writer": neon_writer, "neon_reader": neon_reader},
)
