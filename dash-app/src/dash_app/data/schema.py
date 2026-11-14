"""Static metadata describing the read-only database tables.

The schema is documented here rather than discovered from ``information_schema`` so
column descriptions are available offline and tests stay deterministic. Keep this in
sync with ``queries.CITY_COLUMNS`` and ``queries._DAILY_COLUMNS``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    description: str
    key: str | None = None


@dataclass(frozen=True)
class TableSchema:
    name: str
    summary: str
    grain: str
    columns: tuple[Column, ...]


CITIES_SCHEMA = TableSchema(
    name="cities",
    summary=(
        "Metadata for the 140 cities in the dataset: location, administrative "
        "details and the ERA5 grid cell used for each city."
    ),
    grain="One row per city. Primary key: id.",
    columns=(
        Column("id", "text", "Slug identifier, for example phoenix-us.", "PK"),
        Column("name", "text", "City name."),
        Column("country", "text", "Country name."),
        Column("country_code", "text", "ISO 3166-1 alpha-2 country code."),
        Column("continent", "text", "Continent name."),
        Column("latitude", "double precision", "City latitude in WGS84 degrees."),
        Column("longitude", "double precision", "City longitude in WGS84 degrees."),
        Column(
            "cell_lat", "double precision", "Latitude of the ERA5 grid-cell centre."
        ),
        Column(
            "cell_lon", "double precision", "Longitude of the ERA5 grid-cell centre."
        ),
        Column("population", "integer", "City population."),
        Column("is_capital", "boolean", "Whether the city is a national capital."),
        Column("latitude_band", "text", "Climate band derived from latitude."),
        Column(
            "coast_distance_km", "real", "Distance from the city to the coast in km."
        ),
        Column("coastal", "boolean", "Whether the city is classified as coastal."),
        Column("priority", "integer", "Loading priority assigned by the pipeline."),
        Column("download_order", "integer", "Order in which cities were downloaded."),
        Column("era5_lat", "double precision", "Latitude used for the ERA5 request."),
        Column("era5_lon", "double precision", "Longitude used for the ERA5 request."),
        Column("era5_elevation", "real", "ERA5 grid-cell elevation in metres."),
    ),
)

DAILY_SCHEMA = TableSchema(
    name="daily",
    summary=(
        "Daily minimum, mean and maximum temperatures from ERA5 for every city, "
        "from 1940 onwards. ERA5 data arrives about a week late."
    ),
    grain=(
        "One row per city and day. Primary key: (city_id, date). "
        "Foreign key: city_id references cities.id."
    ),
    columns=(
        Column(
            "city_id",
            "text",
            "City identifier referencing cities.id.",
            "PK, FK",
        ),
        Column("date", "date", "Observation date.", "PK"),
        Column("t_mean", "real", "Daily mean temperature in degrees Celsius."),
        Column("t_max", "real", "Daily maximum temperature in degrees Celsius."),
        Column("t_min", "real", "Daily minimum temperature in degrees Celsius."),
    ),
)

SCHEMAS: dict[str, TableSchema] = {
    "cities": CITIES_SCHEMA,
    "daily": DAILY_SCHEMA,
}
