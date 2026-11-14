# Climate Analytics

Historical analysis of the temperature across the world: **140 cities, every day from 1940 to
2025**, from the [Open-Meteo](https://open-meteo.com/) API (ERA5 reanalysis) to annual statistics
and distribution "bells" that show how the climate of each city has changed.

## Main results

- **Every city is warmer** in 2016–2025 than in 1961–1990: median **+1.11 °C**, and in 109 of the
  140 cities the warmest year is 2015 or later.
- Warming speeds up after 1980: median trend **+0.27 °C per decade since 1975** (+0.19 since 1940).
- **Inland cities warm more than coastal ones** (+1.46 °C vs +0.87 °C), and high latitudes more
  than the tropics (polar +2.67 °C, temperate +1.55 °C, tropical +0.83 °C).
- **The whole distribution of days moves to the warm side**; in cold climates the cold days
  warm the most (the coldest 5 % of days are +5.0 °C warmer in Anchorage).

The details, charts and precautions are in the conclusions of each notebook.

## Repository layout

```
climate-analytics/
├── data/
│   └── cities.csv            # the 140 cities (the only data file in git)
├── notebooks/                # one notebook per step, run in order
│   ├── 01_explore_api.ipynb
│   ├── 02_city_list.ipynb
│   ├── 03_download.ipynb
│   ├── 04_annual_stats.ipynb
│   └── 05_bells.ipynb
├── packages/                 # uv workspace
│   ├── pipelines/            # getting the data
│   │   └── src/pipelines/
│   │       ├── open_meteo.py     # API client and call-cost formula
│   │       ├── cities.py         # city selection (Natural Earth)
│   │       ├── download.py       # resumable download into SQLite, import/export
│   │       ├── neon.py           # loads the shared data into Neon (PostgreSQL)
│   │       └── update.py         # adds the newest days to Neon
│   └── analysis/             # analysing it
│       └── src/analysis/
│           ├── stats.py          # annual statistics, anomalies and trends
│           ├── bells.py          # distribution curves (kernel density, days per °C)
│           └── plots.py          # charts
└── dash-app/                 # web app (standalone uv project)
```

The packages hold the reusable code, with tests; the notebooks explain each step and run it.

## Setup

Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 if needed).

```bash
git clone https://github.com/FelitoAguila/climate-analytics.git
cd climate-analytics
uv sync                    # creates .venv with every package and dependency
uv run jupyter lab         # open the notebooks
```

## Getting the data

The daily data (4.4 million rows, ~250 MB as SQLite) are **not in git**: notebook
`03_download.ipynb` creates `data/climate.db` in one of three ways, checked in this order:

1. **Shared copy (recommended):** ask a team member for **`climate.parquet`** (~25 MB) and put it
   in `data/`. Notebook 03 validates and imports it in a few seconds.
2. **Original project:** if the `clima-mundial` project is next to this repository, its database
   (`../clima-mundial/data/clima.db`) is imported.
3. **From the API:** otherwise, notebook 03 downloads the cities from Open-Meteo. The free tier
   allows ~13 cities a day, so the 140 cities take **about 11 days**: run the notebook once a
   day; it resumes where it stopped.

Whoever has the complete database can write `data/climate.parquet` for the others (section 7 of
notebook 03).

### Loading the data into Neon

The web app will read the data from [Neon](https://neon.com/) (PostgreSQL in the cloud). With
`data/climate.parquet` in place:

```bash
cp .env.example .env       # then paste your connection string (direct, without -pooler)
uv run load-neon --limit 2 # test with two cities
uv run load-neon           # every city; running it again only loads what is missing
```

After that first load, `uv run update-neon` adds the newest days of every city. ERA5 arrives about
a week late, so the database never reaches today.

`.env` holds the database password: git ignores it, so never commit or share it.

To read without being able to change anything, create a read-only user once, in the Neon SQL Editor
(not in the Neon Console: the roles created there are administrators):

```sql
CREATE ROLE climate_reader LOGIN PASSWORD 'a-long-random-password';
GRANT CONNECT ON DATABASE neondb TO climate_reader;
GRANT USAGE ON SCHEMA public TO climate_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO climate_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO climate_reader;
```

Its connection string is the same one with this user and password. Share it only privately.

### Daily update with Airflow

`airflow/dags/neon_daily_update.py` runs the update and checks the data, with
[Apache Airflow](https://airflow.apache.org/):

```
update_neon >> [data_is_fresh, no_missing_days, temperatures_are_consistent]
```

- `update_neon` (`BashOperator`) runs `uv run update-neon`, which reads `.env` as usual.
- The three checks (`SQLCheckOperator`) use the read-only Airflow connection `neon_reader`. They fail
  if a city is more than `max_days_behind` days behind (10 by default; it can be changed when
  triggering the DAG), if a day is missing, or if `t_min > t_mean` or `t_mean > t_max`.
- One retry after 10 minutes if a task fails.

#### In production: GitHub Actions

`.github/workflows/airflow-daily.yml` runs the DAG every day at 13:00 UTC (10:00 in São Paulo): it
installs the project and Airflow on a clean machine and runs `airflow dags test neon_daily_update`
once. GitHub's cron plays the role of Airflow's scheduler, so no server is needed. It needs two
repository secrets (Settings → Secrets and variables → Actions):

| Secret | Used for |
|---|---|
| `DATABASE_URL` | `update-neon` writes with it |
| `READONLY_DATABASE_URL` | Becomes the Airflow connection `neon_reader` (`AIRFLOW_CONN_NEON_READER`) |

Run it by hand with **Actions → Airflow daily update → Run workflow** (`max_days_behind` can be
changed there; 1 tests a failure). A failed run is marked in red and GitHub sends an email. There is
no Airflow web panel in production: each run's log stays in the Actions tab. GitHub may start the
scheduled run some minutes late, and it pauses scheduled workflows after 60 days without activity in
the repository (re-enable them in the Actions tab).

#### On your computer: to learn and develop

The same DAG runs locally with the Airflow web panel. Its schedule (every day at 10:00, São Paulo
time, without catching up the days the computer was off) only applies while Airflow is running.

**Install** (once): Airflow pins hundreds of versions, so it has its own environment.

```bash
uv venv --python 3.12 .venv-airflow
uv pip install -p .venv-airflow/bin/python "apache-airflow==3.4.0" apache-airflow-providers-postgres pytest \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.4.0/constraints-3.12.txt"
```

**Start** it with `./airflow/start.sh` and open http://localhost:8080. The user is `admin`; its
password is in `airflow/simple_auth_manager_passwords.json.generated`. Everything Airflow generates
in `airflow/` is ignored by git, except the DAGs, the tests and the start script.

**Connection** (once): in **Admin → Connections**, add `neon_reader` of type Postgres with the
read-only user: host, database `neondb`, login `climate_reader`, its password, port 5432 and the
extra `{"sslmode": "require"}`.

**Tests:** `.venv-airflow/bin/python -m pytest airflow/tests` (`uv run pytest` skips them).

## Notebooks

| Notebook | What it does | Needs |
|---|---|---|
| `01_explore_api` | One city (Madrid): response format, data quality, why ERA5, call cost | internet, ~690 API calls |
| `02_city_list` | Selects 140 cities spread over the world → `data/cities.csv` | internet (23 MB from Natural Earth) |
| `03_download` | Fills `data/climate.db` (import or download), shares it as Parquet | data or API |
| `04_annual_stats` | Annual means, anomalies vs 1961–1990, trends, warming stripes | `data/climate.db` |
| `05_bells` | Distribution of the days of each year and decade, cold vs hot days | `data/climate.db` |

Notebooks 04 and 05 take about a minute each and do not call any API.

## Tests and lint

```bash
uv run pytest packages                 # no network needed (dash-app has its own tests)
uv run ruff check notebooks packages
uv run ruff format notebooks packages
```

The same checks run automatically on GitHub (`.github/workflows/ci.yml`) on every pull request and
on every push to `main`: `ruff check`, `ruff format --check` and `pytest`, after `uv sync --locked`
(which fails if `uv.lock` is out of date). The pull request shows a green check or a red cross; run
the commands above before pushing to see the same result. It needs no secrets.

## Data sources

- **Temperatures:** [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
  ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)), ERA5 reanalysis by
  Copernicus/ECMWF. Always requested with `models=era5`, so the whole series comes from one source.
- **Cities, countries and coastline:** [Natural Earth](https://www.naturalearthdata.com/) v5.1.2
  (public domain).

## Precautions

- ERA5 has far fewer observations **before 1950**, and a few cities show blocks of unusual years
  before ~1960 that may come from the model rather than the climate.
- Each city is an **ERA5 grid cell of about 25 km**, not a weather station: the urban heat island
  is not captured.
- Natural Earth places **Vila Velha** (Brazil) about 2,500 km from the real city (in Amapá), so its
  series is the climate of that point.
