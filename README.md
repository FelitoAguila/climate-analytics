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
└── packages/                 # uv workspace
    ├── pipelines/            # getting the data
    │   └── src/pipelines/
    │       ├── open_meteo.py     # API client and call-cost formula
    │       ├── cities.py         # city selection (Natural Earth)
    │       └── download.py       # resumable download into SQLite, import/export
    ├── analysis/             # analysing it
    │   └── src/analysis/
    │       ├── stats.py          # annual statistics, anomalies and trends
    │       ├── bells.py          # distribution curves (kernel density, days per °C)
    │       └── plots.py          # charts
    └── dash_app/             # web app (not started yet)
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
uv run pytest                          # no network needed
uv run ruff check notebooks packages
uv run ruff format notebooks packages
```

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
