#!/usr/bin/env bash
# Starts Airflow on this computer, to learn: the web panel (http://localhost:8080), the
# scheduler and its database (SQLite), all in one terminal. Stop it with Ctrl+C.
#
# Run it from anywhere: ./airflow/start.sh
# The first time, Airflow creates the user "admin" and shows its password in this terminal
# (it also keeps it in airflow/simple_auth_manager_passwords.json.generated).
set -euo pipefail

cd "$(dirname "$0")/.."               # the project root
export AIRFLOW_HOME="$PWD/airflow"     # config, database and logs (ignored by git)
export AIRFLOW__CORE__LOAD_EXAMPLES=False  # only our DAGs, not the dozens of examples

# standalone starts each piece with the `airflow` command, so it must be on the PATH
export PATH="$PWD/.venv-airflow/bin:$PATH"

exec airflow standalone
