"""About page: what Climate Analytics is, where the data comes from and how it works."""

from __future__ import annotations

from dash import dcc, html

from .. import config
from ..components import bulma as b

_OVERVIEW = """
## About Climate Analytics

Climate Analytics is a web application for exploring how the climate has changed in
**140 cities around the world**, using **daily temperature records from 1940 onwards**.
The data comes from the Open-Meteo historical weather API and the ERA5 reanalysis, and the
app reads it from a Neon PostgreSQL database.

### What the data shows

In the project's comparison of 2016–2025 with the 1961–1990 reference period:

- every one of the 140 cities was warmer, with a median increase of about **+1.1 °C**;
- in 109 cities, the warmest year is 2015 or later;
- warming accelerated after 1980, reaching a median trend of about
  **+0.27 °C per decade since 1975**;
- inland cities warmed more than coastal ones, and high-latitude cities more than
  tropical ones;
- the whole distribution of daily temperatures moved warmer, not just the averages.

### How it works

1. Open-Meteo provides daily minimum, mean and maximum temperatures from ERA5.
2. The pipelines package downloads, validates and loads the data into Neon.
3. A scheduled Airflow DAG adds the newest days and checks coverage, gaps and temperature
   consistency.
4. This Dash application reads the database with a read-only user and turns it into tables
   and charts.

Each city is represented by one ERA5 grid cell of about 25 km, not by a weather station, so
the urban heat island is not captured. ERA5 arrives about a week late, so the database never
reaches today.

### Data sources

- **Temperatures:** [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api),
  ERA5 reanalysis by Copernicus/ECMWF, licensed under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Cities and coastline:** [Natural Earth](https://www.naturalearthdata.com/), public
  domain.

### Built with

Plotly Dash, Plotly, pandas, SQLAlchemy, psycopg, Neon PostgreSQL, Bulma and Font Awesome.
The interface is inspired by the [Materials Project](https://materialsproject.org) website.

### Project links

- [Source code on GitHub](https://github.com/FelitoAguila/climate-analytics)
- [Explore the feature dashboard](/features)
- [Read the project README](https://github.com/FelitoAguila/climate-analytics#readme)
"""


def _author_card(author: config.Author) -> html.Div:
    links = [
        html.A(
            [
                html.Span(html.I(className=item.icon), className="icon"),
                html.Span(item.label),
            ],
            href=item.href,
            target="_blank",
            rel="noopener",
            className="mp-author-link",
        )
        for item in author.links
    ]
    return b.card(
        b.card_content(
            [
                b.title(author.name, size=5),
                html.Div(links, className="mp-author-links"),
            ]
        ),
        className="mp-author-card",
    )


def layout() -> html.Div:
    return b.section(
        b.container(
            [
                b.breadcrumb([("Home", "/"), ("About", "/about")]),
                b.box(dcc.Markdown(_OVERVIEW, className="content")),
                html.Div(
                    [
                        b.title("Authors", size=4, id="authors"),
                        b.columns(
                            [
                                b.column(_author_card(author))
                                for author in config.AUTHORS
                            ],
                            multiline=True,
                        ),
                    ],
                    className="box",
                ),
            ],
            style={"maxWidth": "900px"},
        )
    )
