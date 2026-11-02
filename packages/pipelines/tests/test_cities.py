import numpy as np
import pandas as pd
import pytest
from pipelines.cities import (
    Coastline,
    distance_to_coast_km,
    era5_cell,
    farthest_point_selection,
    haversine_km,
    latitude_band,
    make_slug,
    select_cities,
)


def test_haversine_madrid_barcelona():
    assert haversine_km(40.4168, -3.7038, 41.3874, 2.1686) == pytest.approx(505, abs=2)


def test_slug():
    assert make_slug("São Paulo") == "sao-paulo"
    assert make_slug("St. John's") == "st-john-s"


@pytest.mark.parametrize(
    ("latitude", "band"),
    [
        (0.0, "tropical_north"),
        (-23.44, "subtropical_south"),
        (55.86, "temperate_north"),  # Glasgow
        (64.1, "subpolar_north"),
        (69.3, "polar_north"),
    ],
)
def test_latitude_band(latitude, band):
    assert latitude_band(latitude) == band


def test_era5_cell():
    assert era5_cell(40.4168) == 40.5
    assert era5_cell(-3.7038) == -3.75


def test_distance_to_a_long_straight_segment():
    # A coast along the equator, with vertices 220 km apart; a city 1 km north of its middle
    coast = Coastline.from_lines([np.array([[0.0, 0.0], [2.0, 0.0]])])
    to_vertices, final = distance_to_coast_km(coast, [0.009], [1.0])
    assert to_vertices[0] > 100
    assert final[0] == pytest.approx(1.0, abs=0.05)


def test_coastline_lines_round_trip():
    lines = [
        np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]]),
        np.array([[5.0, 5.0], [6.0, 5.0]]),
    ]
    coast = Coastline.from_lines(lines)
    assert len(coast.segment_start) == 3
    for original, rebuilt in zip(lines, coast.lines(), strict=True):
        assert (original == rebuilt).all()


def toy_cities():
    # Sorted by population, as build_candidates returns them
    return pd.DataFrame(
        {
            "id": ["a", "b", "c", "d", "e"],
            "latitude": [0.0, 0.0, 0.0, 10.0, 0.5],
            "longitude": [0.0, 1.0, 50.0, 0.0, 0.5],
            "population": [5e6, 4e6, 3e5, 2e5, 1e5],
        }
    )


def test_farthest_point_starts_with_the_first_row():
    chosen = farthest_point_selection(toy_cities(), 3)
    # a (largest), then c (50° away), then d (10° from a, the biggest remaining gap)
    assert chosen["id"].tolist() == ["a", "c", "d"]


def test_forced_cities_take_a_place_in_their_priority():
    chosen = select_cities(
        toy_cities(), {1: 2, 2: 2}, force={"e": 2}, min_population_priority_1=1e6
    )
    assert len(chosen) == 4
    assert chosen.loc[chosen["id"] == "e", "priority"].item() == 2
    # Priority 1 only has cities of at least one million
    assert set(chosen.loc[chosen["priority"] == 1, "id"]) == {"a", "b"}
    assert chosen["order"].tolist() == [1, 2, 3, 4]
