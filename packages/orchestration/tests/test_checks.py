from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta

import dagster as dg
from orchestration import assets, checks
from orchestration.resources import NeonResource
from pipelines.update import Summary


class FakeCursor:
    def __init__(self, row=None, rows=()):
        self.row, self.rows = row, list(rows)

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeNeon(NeonResource):
    """Answers every query with the same prepared result."""

    def connect(self):
        @contextmanager
        def connection():
            yield type("C", (), {"execute": lambda _, *args: CURSOR})()

        return connection()


CURSOR = FakeCursor()


def run_check(check, cursor):
    global CURSOR
    CURSOR = cursor
    result = dg.materialize(
        [assets.daily_temperatures, check],
        selection=dg.AssetSelection.checks(check),
        resources={
            "neon_writer": FakeNeon(url="unused"),
            "neon_reader": FakeNeon(url="unused"),
        },
        raise_on_error=False,
    )
    return result.get_asset_check_evaluations()[0]


def test_days_behind():
    assert checks.days_behind(date(2026, 11, 2), date(2026, 11, 9)) == 7


def test_fresh_data_passes_and_old_data_fails():
    today = datetime.now(UTC).date()
    fresh = run_check(
        checks.data_is_fresh, FakeCursor(row=(today - timedelta(days=7), today))
    )
    old = run_check(
        checks.data_is_fresh, FakeCursor(row=(today - timedelta(days=11), today))
    )
    assert fresh.passed and not old.passed
    assert old.metadata["days_behind"].value == 11


def test_a_gap_fails():
    result = run_check(checks.no_missing_days, FakeCursor(rows=[("madrid-es", 3)]))
    assert not result.passed
    assert result.metadata["examples"].value == "madrid-es (3 days)"
    assert run_check(checks.no_missing_days, FakeCursor(rows=[])).passed


def test_impossible_temperatures_fail():
    assert not run_check(
        checks.temperatures_are_consistent, FakeCursor(row=(2,))
    ).passed
    assert run_check(checks.temperatures_are_consistent, FakeCursor(row=(0,))).passed


def test_a_failed_blocking_check_fails_the_whole_run(monkeypatch):
    global CURSOR
    CURSOR = FakeCursor(row=(1,))  # one impossible day
    monkeypatch.setattr(assets, "read_cities", lambda connection: [])
    monkeypatch.setattr(assets, "update", lambda *args: Summary())
    result = dg.materialize(
        [assets.daily_temperatures, checks.temperatures_are_consistent],
        resources={
            "neon_writer": FakeNeon(url="unused"),
            "neon_reader": FakeNeon(url="unused"),
        },
        raise_on_error=False,
    )
    assert not result.success
    # It failed because of the check, after the update had worked
    assert result.asset_materializations_for_node("daily_temperatures")
    assert not result.get_asset_check_evaluations()[0].passed


def test_the_freshness_limit_can_be_changed(monkeypatch):
    today = datetime.now(UTC).date()
    monkeypatch.setenv("MAX_DAYS_BEHIND", "5")
    result = run_check(
        checks.data_is_fresh, FakeCursor(row=(today - timedelta(days=7), today))
    )
    assert not result.passed
    assert result.metadata["max_days_behind"].value == 5
