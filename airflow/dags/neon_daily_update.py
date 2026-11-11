"""DAG `neon_daily_update`: adds the newest days to the Neon database and checks them.

Airflow reads this file and shows the DAG in its web panel (http://localhost:8080).
In production, GitHub Actions runs it once a day (.github/workflows/airflow-daily.yml).

    update_neon >> [data_is_fresh, no_missing_days, temperatures_are_consistent]

Every day at 10:00 (São Paulo time): first the update; then three quality checks, at the same time, with the read-only connection
`neon_reader` (created in Admin → Connections). A check fails when its query returns false.
"""

from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.providers.common.sql.operators.sql import SQLCheckOperator
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param

# The project root: this file is in airflow/dags/
PROJECT = Path(__file__).resolve().parents[2]

with DAG(
    dag_id="neon_daily_update",
    description="Adds the newest days of every city to Neon and checks the data",
    start_date=pendulum.datetime(2026, 11, 1, tz="America/Sao_Paulo"),
    # Every day at 10:00 in this time zone (cron: minute hour day month weekday). The scheduler
    # only launches it while Airflow is running and the computer is awake.
    schedule="0 10 * * *",
    # Do not launch the days the computer was off: one update already catches up every day
    catchup=False,
    # If a task fails (for example, no internet), try it once more 10 minutes later
    default_args={"retries": 1, "retry_delay": timedelta(minutes=10)},
    tags=["neon", "climate"],
    params={
        # ERA5 arrives about 7 days late; 10 leaves room for a day or two without updates.
        # It can be changed when triggering the DAG by hand (for example, to test a failure).
        "max_days_behind": Param(10, type="integer", minimum=0),
    },
) as dag:
    # Runs `uv run update-neon` with the project's own environment and its .env file.
    # If a city fails, the command ends with an error and the task turns red.
    update_neon = BashOperator(
        task_id="update_neon",
        bash_command=f"cd {PROJECT} && uv run update-neon",
    )

    # Every city reaches at most max_days_behind days before today
    data_is_fresh = SQLCheckOperator(
        task_id="data_is_fresh",
        conn_id="neon_reader",
        sql="""
            SELECT MIN(last_day) >= CURRENT_DATE - {{ params.max_days_behind }}
            FROM (SELECT MAX(date) AS last_day FROM daily GROUP BY city_id) AS cities
        """,
    )

    # Each city has every day between its first and its last date
    no_missing_days = SQLCheckOperator(
        task_id="no_missing_days",
        conn_id="neon_reader",
        sql="""
            SELECT COUNT(*) = 0
            FROM (SELECT city_id FROM daily GROUP BY city_id
                  HAVING MAX(date) - MIN(date) + 1 <> COUNT(*)) AS cities_with_gaps
        """,
    )

    # No day has its minimum above its mean, or its mean above its maximum
    temperatures_are_consistent = SQLCheckOperator(
        task_id="temperatures_are_consistent",
        conn_id="neon_reader",
        sql="SELECT COUNT(*) = 0 FROM daily WHERE NOT (t_min <= t_mean AND t_mean <= t_max)",
    )

    update_neon >> [data_is_fresh, no_missing_days, temperatures_are_consistent]
