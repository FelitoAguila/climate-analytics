import os
from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest
from pipelines.download import CITY_COLUMNS, check_shared_city
from pipelines.neon import (
    CITY_INSERT,
    cities_to_load,
    city_row,
    connect,
    daily_rows,
    database_url,
    read_shared_data,
)


def shared_rows(city_id="madrid-es"):
    return pd.DataFrame(
        {
            "city_id": city_id,
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "t_mean": [5.0, 6.5],
            "t_max": [10.0, 11.0],
            "t_min": [1.0, 2.0],
            "era5_lat": 40.5,
            "era5_lon": -3.75,
            "era5_elevation": 667.0,
        }
    )


@pytest.fixture
def in_empty_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # load_dotenv writes to the environment: patch.dict restores it after each test
    with patch.dict(os.environ):
        os.environ.pop("DATABASE_URL", None)
        yield tmp_path


def test_missing_url_says_what_to_do(in_empty_folder):
    with pytest.raises(SystemExit, match=r"\.env\.example"):
        database_url()


def test_the_example_url_is_not_accepted(in_empty_folder):
    (in_empty_folder / ".env").write_text(
        "DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require\n"
    )
    with pytest.raises(SystemExit, match="not set"):
        database_url()


def test_url_is_read_from_the_env_file(in_empty_folder):
    (in_empty_folder / ".env").write_text("DATABASE_URL=postgresql://real/db\n")
    assert database_url() == "postgresql://real/db"


def test_a_city_with_a_missing_day_is_rejected():
    rows = pd.concat(
        [shared_rows(), shared_rows().assign(date=pd.Timestamp("2024-01-04"))]
    )
    with pytest.raises(ValueError, match="madrid-es"):
        check_shared_city("madrid-es", rows, "climate.parquet")


def test_a_failed_connection_does_not_show_the_url():
    secret = "s3cret-password"
    with pytest.raises(SystemExit) as failure:
        connect(f"this is not a url {secret}")
    assert secret not in str(failure.value)
    assert failure.value.__cause__ is None
    assert failure.value.__suppress_context__


def test_missing_parquet_says_what_to_do(in_empty_folder):
    with pytest.raises(SystemExit, match="03_download"):
        read_shared_data(in_empty_folder / "climate.parquet")


def test_read_shared_data_groups_by_city(tmp_path):
    path = tmp_path / "climate.parquet"
    data = pd.concat([shared_rows("madrid-es"), shared_rows("tokyo-jp")])
    data["city_id"] = data["city_id"].astype("category")
    data.to_parquet(path, index=False)
    shared = read_shared_data(path)
    assert sorted(shared) == ["madrid-es", "tokyo-jp"]
    assert len(shared["tokyo-jp"]) == 2


def test_only_incomplete_cities_are_loaded():
    shared = {"a": shared_rows("a"), "b": shared_rows("b"), "c": shared_rows("c")}
    loaded = {"a": 2, "b": 1}  # a is complete, b lost days, c was never loaded
    assert cities_to_load(["a", "b", "c", "not-in-file"], shared, loaded) == ["b", "c"]
    assert cities_to_load(["a"], shared, loaded) == []


def test_daily_rows_have_real_dates_and_the_table_order():
    assert daily_rows("madrid-es", shared_rows()) == [
        ("madrid-es", date(2024, 1, 1), 5.0, 10.0, 1.0),
        ("madrid-es", date(2024, 1, 2), 6.5, 11.0, 2.0),
    ]


def test_city_row_matches_the_insert():
    city = pd.Series({column: column for column in CITY_COLUMNS})
    row = city_row(city, shared_rows())
    assert row[-3:] == [40.5, -3.75, 667.0]
    assert len(row) == CITY_INSERT.split("VALUES")[1].count("%s")
    assert "download_order" in CITY_INSERT and '"order"' not in CITY_INSERT
