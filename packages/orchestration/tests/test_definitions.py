from orchestration.definitions import defs


def test_the_daily_job_runs_the_update_and_its_three_checks():
    job = defs.resolve_job_def("daily_update")
    assert sorted(node.name for node in job.nodes) == [
        "daily_temperatures",
        "daily_temperatures_data_is_fresh",
        "daily_temperatures_no_missing_days",
        "daily_temperatures_temperatures_are_consistent",
    ]
