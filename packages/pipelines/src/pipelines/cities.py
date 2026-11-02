"""City list: candidates from Natural Earth and a spread-out selection of them.

The selection is deterministic (no random numbers): it starts from the most populated
candidate and each new city is the one farthest from all the cities already chosen
("farthest point" selection), so the cities cover the whole map instead of piling up
where there are many large cities.
"""

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# Natural Earth (public domain), pinned version so the result is reproducible
NATURAL_EARTH_VERSION = "v5.1.2"
NATURAL_EARTH_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    f"{NATURAL_EARTH_VERSION}/geojson"
)

EARTH_RADIUS_KM = 6371.0
ERA5_CELL_SIZE = 0.25  # degrees

# The places file and the countries file use different codes for South Sudan
COUNTRY_CODE_FIXES = {"SSD": "SDS"}
EXCLUDED_PLACE_TYPES = [
    "Scientific station",
    "Meteorological Station",
    "Historic place",
]
CONTINENT_NAMES = {"Seven seas (open ocean)": "Oceanic islands"}

# Lower limit of each band, in absolute degrees of latitude (the lower limit is included)
LATITUDE_BANDS = [
    (66.56, "polar"),
    (60.0, "subpolar"),
    (35.0, "temperate"),
    (23.44, "subtropical"),
    (0.0, "tropical"),
]


def download_source(name: str, folder: Path) -> Path:
    """Downloads a Natural Earth GeoJSON into `folder`, unless it is already there."""
    path = folder / f"{name}.geojson"
    if not path.exists():
        folder.mkdir(parents=True, exist_ok=True)
        response = requests.get(f"{NATURAL_EARTH_URL}/{name}.geojson", timeout=120)
        response.raise_for_status()
        path.write_bytes(response.content)
    return path


def read_properties(path: Path) -> pd.DataFrame:
    """The `properties` of every feature of a GeoJSON, as a DataFrame."""
    with open(path, encoding="utf-8") as f:
        features = json.load(f)["features"]
    return pd.DataFrame([feature["properties"] for feature in features])


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km. Works with numbers or numpy arrays."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def make_slug(text: str) -> str:
    """'São Paulo' -> 'sao-paulo'"""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def latitude_band(latitude: float) -> str:
    """Climate band from the absolute latitude, with a _north/_south suffix."""
    band = next(name for lower, name in LATITUDE_BANDS if abs(latitude) >= lower)
    return band + ("_north" if latitude >= 0 else "_south")


def era5_cell(degrees):
    """Nearest multiple of 0.25°: the ERA5 grid cell the API will most likely return."""
    return np.round(np.asarray(degrees) / ERA5_CELL_SIZE) * ERA5_CELL_SIZE


def build_candidates(
    places: pd.DataFrame,
    countries: pd.DataFrame,
    min_population: int,
    min_population_capital: int = 0,
    exclude: list[str] | None = None,
) -> pd.DataFrame:
    """Candidate cities: country capitals and cities above `min_population`.

    `places` and `countries` are the properties of ne_10m_populated_places and
    ne_50m_admin_0_countries. The result is sorted by population (largest first), which
    breaks ties later on, and has a stable `id` like 'madrid-es'.
    """
    places = places.assign(ADM0_A3=places["ADM0_A3"].replace(COUNTRY_CODE_FIXES))
    countries = countries[["ADM0_A3", "NAME", "CONTINENT"]].rename(
        columns={"NAME": "country", "CONTINENT": "continent"}
    )
    places = places.merge(countries, on="ADM0_A3", how="left").dropna(
        subset=["continent"]
    )

    is_capital = places["FEATURECLA"] == "Admin-0 capital"
    is_candidate = (
        ~places["FEATURECLA"].isin(EXCLUDED_PLACE_TYPES)
        & (places["continent"] != "Antarctica")
        & (
            (places["POP_MAX"] >= min_population)
            | (is_capital & (places["POP_MAX"] >= min_population_capital))
        )
    )
    candidates = places[is_candidate].copy()
    candidates["is_capital"] = is_capital[is_candidate].astype(int)
    candidates["continent"] = candidates["continent"].replace(CONTINENT_NAMES)

    # Country code: ISO 2 letters; when there is none ("-99"), the 3-letter one
    candidates["country_code"] = candidates["ISO_A2"].where(
        candidates["ISO_A2"] != "-99", candidates["ADM0_A3"]
    )
    candidates = candidates.sort_values(
        ["POP_MAX", "NAMEASCII"], ascending=[False, True]
    ).reset_index(drop=True)

    candidates["id"] = [
        f"{make_slug(name)}-{code.lower()}"
        for name, code in zip(candidates["NAMEASCII"], candidates["country_code"])
    ]
    # Two cities with the same name in the same country: the smaller one gets -2, -3...
    repetition = candidates.groupby("id").cumcount()
    candidates.loc[repetition > 0, "id"] += "-" + (
        repetition[repetition > 0] + 1
    ).astype(str)
    candidates = candidates[~candidates["id"].isin(exclude or [])]

    candidates = candidates.rename(
        columns={
            "NAME": "name",
            "LATITUDE": "latitude",
            "LONGITUDE": "longitude",
            "POP_MAX": "population",
        }
    )
    candidates["latitude_band"] = candidates["latitude"].apply(latitude_band)
    candidates["cell_lat"] = era5_cell(candidates["latitude"])
    candidates["cell_lon"] = era5_cell(candidates["longitude"])
    return candidates.reset_index(drop=True)


@dataclass
class Coastline:
    """Coastline vertices and the straight segments that join consecutive vertices."""

    lat: np.ndarray
    lon: np.ndarray
    segment_start: np.ndarray  # index of the first vertex of each segment
    segment_end: np.ndarray
    max_segment_km: float

    @classmethod
    def from_lines(cls, lines: list[np.ndarray]) -> "Coastline":
        """`lines`: arrays of (lon, lat) vertices, one per coastline."""
        points = np.vstack(lines)
        line_start = np.cumsum([0] + [len(line) for line in lines[:-1]])
        start = np.concatenate(
            [first + np.arange(len(line) - 1) for first, line in zip(line_start, lines)]
        )
        end = start + 1
        lon, lat = points[:, 0], points[:, 1]
        lengths = haversine_km(lat[start], lon[start], lat[end], lon[end])
        return cls(lat, lon, start, end, float(lengths.max()))

    @classmethod
    def from_geojson(cls, path: Path) -> "Coastline":
        with open(path, encoding="utf-8") as f:
            features = json.load(f)["features"]
        lines = []
        for feature in features:
            geometry = feature["geometry"]
            if geometry["type"] == "LineString":
                lines.append(np.array(geometry["coordinates"]))
            else:  # MultiLineString
                lines.extend(np.array(line) for line in geometry["coordinates"])
        return cls.from_lines(lines)

    def lines(self) -> list[np.ndarray]:
        """The coastlines again, as arrays of (lon, lat) vertices (for drawing)."""
        is_last = np.ones(len(self.lat), dtype=bool)
        is_last[self.segment_start] = (
            False  # every vertex but the last starts a segment
        )
        points = np.column_stack([self.lon, self.lat])
        return np.split(points, np.flatnonzero(is_last)[:-1] + 1)


def project_local_km(lat, lon, lat0, lon0):
    """Equirectangular projection centred on (lat0, lon0): x (east) and y (north) in km."""
    dlon = (lon - lon0 + 180) % 360 - 180  # avoids the jump at the date line (±180°)
    x = np.radians(dlon) * EARTH_RADIUS_KM * np.cos(np.radians(lat0))
    y = np.radians(lat - lat0) * EARTH_RADIUS_KM
    return x, y


def nearest_segment(coast: Coastline, lat0: float, lon0: float, segments: np.ndarray):
    """Closest point to (lat0, lon0) among the given segments.

    Returns (distance in km, x, y) in the local projection, where the city is at (0, 0).
    """
    start, end = coast.segment_start[segments], coast.segment_end[segments]
    ax, ay = project_local_km(coast.lat[start], coast.lon[start], lat0, lon0)
    bx, by = project_local_km(coast.lat[end], coast.lon[end], lat0, lon0)
    # Point of the segment: A + t·(B − A); the t closest to the origin, clipped to [0, 1]
    abx, aby = bx - ax, by - ay
    t = np.clip(-(ax * abx + ay * aby) / np.maximum(abx**2 + aby**2, 1e-12), 0, 1)
    px, py = ax + t * abx, ay + t * aby
    distances = np.sqrt(px**2 + py**2)
    best = np.argmin(distances)
    return distances[best], px[best], py[best]


def distance_to_coast_km(coast: Coastline, latitudes, longitudes, threshold_km=200.0):
    """For each city returns (distance to the vertices, final distance), in km.

    Step 1: haversine to every vertex (exact, but only looks at vertices, which can be more
    than 100 km apart on straight coasts). Step 2: when that is below `threshold_km`, also the
    distance to the segments, in a local projection. The final distance is the smaller one.
    """
    to_vertices = np.empty(len(latitudes))
    final = np.empty(len(latitudes))
    for k, (lat0, lon0) in enumerate(zip(latitudes, longitudes)):
        d_vertices = haversine_km(lat0, lon0, coast.lat, coast.lon)
        to_vertices[k] = final[k] = d_vertices.min()
        if to_vertices[k] < threshold_km:
            # Only segments with an end closer than threshold + longest segment can be closer
            limit = threshold_km + coast.max_segment_km
            near = np.flatnonzero(
                np.minimum(
                    d_vertices[coast.segment_start], d_vertices[coast.segment_end]
                )
                < limit
            )
            if len(near) > 0:
                final[k] = min(final[k], nearest_segment(coast, lat0, lon0, near)[0])
    return to_vertices, final


def farthest_point_selection(
    pool: pd.DataFrame, n: int, previous: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Chooses n cities of `pool`, each one the farthest from those already chosen.

    `previous` are cities chosen before (they count as chosen but are not returned). With no
    previous cities, the first one is the first row of `pool` (the most populated one).
    Adds `distance_when_chosen_km`: how far the city was from the rest when it was chosen.
    """
    lat = pool["latitude"].to_numpy()
    lon = pool["longitude"].to_numpy()

    # Distance from each candidate to the closest chosen city (inf = none chosen yet)
    min_distance = np.full(len(pool), np.inf)
    if previous is not None:
        for lat_prev, lon_prev in zip(previous["latitude"], previous["longitude"]):
            min_distance = np.minimum(
                min_distance, haversine_km(lat, lon, lat_prev, lon_prev)
            )

    positions, distances = [], []
    for _ in range(n):
        following = 0 if np.isinf(min_distance).all() else int(np.argmax(min_distance))
        positions.append(following)
        distances.append(min_distance[following])
        min_distance = np.minimum(
            min_distance, haversine_km(lat, lon, lat[following], lon[following])
        )

    chosen = pool.iloc[positions].copy()
    chosen["distance_when_chosen_km"] = np.round(distances, 0)
    return chosen


def _concat(*tables: pd.DataFrame) -> pd.DataFrame:
    """Concatenates tables, skipping empty ones."""
    non_empty = [table for table in tables if len(table) > 0]
    return pd.concat(non_empty) if non_empty else tables[0]


def select_cities(
    candidates: pd.DataFrame,
    per_priority: dict[int, int],
    force: dict[str, int] | None = None,
    min_population_priority_1: int = 0,
) -> pd.DataFrame:
    """Chooses `per_priority[p]` cities for each download priority p, in order.

    - Priority 1 only takes candidates with at least `min_population_priority_1`.
    - `force` maps id -> priority. A forced city goes first in its priority and takes one of
      its places; the automatic selection fills the rest, starting from all the cities chosen
      so far. A forced city is never chosen automatically in another priority.

    Adds `priority` and `order` (download order, from 1).
    """
    force = force or {}
    chosen = candidates.iloc[0:0]  # empty table with the same columns
    for priority, n in per_priority.items():
        forced_ids = [city for city, p in force.items() if p == priority]
        forced = candidates[candidates["id"].isin(forced_ids)].assign(
            distance_when_chosen_km=np.nan
        )
        pool = candidates[
            ~candidates["id"].isin(chosen["id"]) & ~candidates["id"].isin(list(force))
        ]
        if priority == 1:
            pool = pool[pool["population"] >= min_population_priority_1]
        new = farthest_point_selection(
            pool, n - len(forced), previous=_concat(chosen, forced)
        )
        chosen = _concat(chosen, _concat(forced, new).assign(priority=priority))

    chosen = chosen.reset_index(drop=True)
    chosen["order"] = range(1, len(chosen) + 1)
    return chosen
