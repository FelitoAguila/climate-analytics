from contextlib import contextmanager
from datetime import date

import dagster as dg
import pytest
from orchestration import assets
from orchestration.resources import NeonResource
from pipelines.update import Summary


class FakeNeon(NeonResource):
    """Gives no real connection: the tests replace the functions that would use it."""

    @contextmanager
    def connect(self):
        yield None


@pytest.fixture
def fake_update(monkeypatch):
    def use(summary):
        monkeypatch.setattr(assets, "read_cities", lambda connection: ["a", "b"])
        monkeypatch.setattr(assets, "update", lambda *args: summary)

    return use


def materialize():
    return dg.materialize(
        [assets.daily_temperatures],
        resources={"neon_writer": FakeNeon(url="unused")},
        raise_on_error=False,
    )


def test_the_summary_is_shown_in_dagster(fake_update):
    fake_update(Summary(new_days=7, api_calls=140, complete_until=date(2026, 11, 2)))
    result = materialize()
    assert result.success
    metadata = result.asset_materializations_for_node("daily_temperatures")[0].metadata
    assert metadata["new_days"].value == 7
    assert metadata["complete_until"].value == "2026-11-02"
    assert metadata["cities"].value == 2


def test_a_failed_city_fails_the_run(fake_update):
    fake_update(Summary(failed=["madrid-es"]))
    assert not materialize().success
