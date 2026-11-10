"""Tests of the Airflow DAG. They need Airflow, so they run in its own environment:

    .venv-airflow/bin/python -m pytest airflow/tests

In the project's environment (`uv run pytest`) they are skipped.
"""

from pathlib import Path

import pytest

pytest.importorskip("airflow")

from airflow.dag_processing.dagbag import DagBag

DAGS = Path(__file__).resolve().parents[1] / "dags"
CHECKS = {"data_is_fresh", "no_missing_days", "temperatures_are_consistent"}


@pytest.fixture(scope="module")
def dag(tmp_path_factory, monkeypatch_module):
    # A temporary AIRFLOW_HOME, so the tests never touch your local Airflow
    monkeypatch_module.setenv("AIRFLOW_HOME", str(tmp_path_factory.mktemp("airflow")))
    bag = DagBag(dag_folder=str(DAGS))
    assert bag.import_errors == {}
    return bag.dags["neon_daily_update"]


@pytest.fixture(scope="module")
def monkeypatch_module():
    with pytest.MonkeyPatch.context() as patch:
        yield patch


def test_the_update_runs_first_and_then_the_three_checks(dag):
    assert set(dag.task_ids) == {"update_neon", *CHECKS}
    assert dag.get_task("update_neon").downstream_task_ids == CHECKS
    for check in CHECKS:
        assert dag.get_task(check).conn_id == "neon_reader"  # the read-only user


def test_it_runs_every_day_at_ten_without_catching_up(dag):
    assert dag.timetable.expression == "0 10 * * *"
    assert str(dag.timezone) == "America/Sao_Paulo"
    assert dag.catchup is False
    assert dag.default_args["retries"] == 1


def test_the_freshness_limit_is_a_parameter(dag):
    assert dag.params["max_days_behind"] == 10
    assert "params.max_days_behind" in dag.get_task("data_is_fresh").sql
