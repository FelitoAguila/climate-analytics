import sqlite3

import pandas as pd
import pytest
from pipelines import download
from pipelines.download import (
    DailyLimitReached,
    DownloadConfig,
    DownloadError,
    fetch_with_retries,
    import_clima_mundial,
    load_cities,
    open_db,
    run_batch,
    usage_24h,
    validate,
)

START, END = "2024-01-01", "2024-01-03"
DATES = ["2024-01-01", "2024-01-02", "2024-01-03"]
CONFIG = DownloadConfig(pause_minutes=0)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Retries and pauses must not really wait in the tests."""
    monkeypatch.setattr(download.time, "sleep", lambda seconds: None)


def payload(t_mean=(5.0, 6.0, 7.0)):
    return {
        "latitude": 40.5,
        "longitude": -3.75,
        "elevation": 666.0,
        "daily": {
            "time": DATES,
            "temperature_2m_mean": list(t_mean),
            "temperature_2m_max": [10.0, 11.0, 12.0],
            "temperature_2m_min": [1.0, 2.0, 3.0],
        },
    }


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text
        self.content = text.encode()

    def json(self):
        if self._body is None:
            raise ValueError("Expecting value")
        return self._body


class FakeApi:
    """Returns the given responses in order and counts the requests."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = 0

    def __call__(self, url, params, timeout):
        self.requests += 1
        return self.responses.pop(0) if self.responses else FakeResponse(body=payload())


def cities(n=2):
    rows = [
        {
            "id": f"city-{i}",
            "name": f"City {i}",
            "country": "X",
            "country_code": "XX",
            "continent": "Europe",
            "latitude": 40.0 + i,
            "longitude": -3.0,
            "cell_lat": 40.0 + i,
            "cell_lon": -3.0,
            "population": 1_000_000,
            "is_capital": 0,
            "latitude_band": "temperate_north",
            "coast_distance_km": 300,
            "coastal": 0,
            "priority": 1,
            "order": i + 1,
        }
        for i in range(n)
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def db(tmp_path):
    connection = open_db(tmp_path / "test.db")
    load_cities(connection, cities())
    yield connection
    connection.close()


def test_validate_accepts_a_good_payload():
    assert validate(payload(), START, END) == []


def test_validate_finds_problems():
    missing_day = payload()
    missing_day["daily"]["time"] = DATES[:2]
    assert "dates: 2 received, 3 expected" in validate(missing_day, START, END)
    assert validate(payload(t_mean=(5.0, None, 7.0)), START, END) == [
        "temperature_2m_mean: 1 empty values"
    ]
    assert validate(payload(t_mean=(5.0, 50.0, 7.0)), START, END) == [
        "1 days with t_min > t_mean or t_mean > t_max"
    ]


def test_empty_200_is_retried_and_charged(db):
    api = FakeApi(FakeResponse(200, None), FakeResponse(200, payload()))
    data = fetch_with_retries(
        db, "city-0", {}, 673.0, CONFIG, log=lambda m: None, get=api
    )
    assert data == payload()
    assert api.requests == 2
    assert usage_24h(db) == 2 * 673.0


def test_daily_limit_stops(db):
    api = FakeApi(FakeResponse(429, {"reason": "Daily API request limit exceeded"}))
    with pytest.raises(DailyLimitReached):
        fetch_with_retries(db, "city-0", {}, 673.0, CONFIG, log=lambda m: None, get=api)


def test_client_error_is_not_retried(db):
    api = FakeApi(FakeResponse(400, {"reason": "Invalid date"}))
    with pytest.raises(DownloadError, match="HTTP 400"):
        fetch_with_retries(db, "city-0", {}, 673.0, CONFIG, log=lambda m: None, get=api)
    assert api.requests == 1


def test_batch_is_resumable(db):
    api = FakeApi()
    assert run_batch(db, START, END, CONFIG, log=lambda m: None, get=api) == 2
    assert api.requests == 2
    assert db.execute("SELECT COUNT(*) FROM daily").fetchone()[0] == 6
    # Second run: everything is complete, so no request at all
    assert run_batch(db, START, END, CONFIG, log=lambda m: None, get=api) == 0
    assert api.requests == 2


def test_batch_stops_at_the_budget(db):
    api = FakeApi()
    config = DownloadConfig(
        pause_minutes=0, daily_budget=1.5
    )  # room for one 1-call request
    assert run_batch(db, START, END, config, log=lambda m: None, get=api) == 1


def test_invalid_data_marks_an_error(db):
    api = FakeApi(FakeResponse(200, payload(t_mean=(5.0, None, 7.0))))
    run_batch(
        db,
        START,
        END,
        DownloadConfig(pause_minutes=0, daily_budget=1.5),
        log=lambda m: None,
        get=api,
    )
    status, error = db.execute(
        "SELECT status, last_error FROM downloads WHERE city_id = 'city-0'"
    ).fetchone()
    assert status == "error" and "empty values" in error
    assert db.execute("SELECT COUNT(*) FROM daily").fetchone()[0] == 0


def test_load_cities_deletes_pending_cities_that_left_the_csv(db):
    removed = load_cities(db, cities(1))
    assert removed == ["city-1"]
    assert db.execute("SELECT COUNT(*) FROM cities").fetchone()[0] == 1


def test_import_clima_mundial(db, tmp_path):
    source = tmp_path / "clima.db"
    with sqlite3.connect(source) as old:
        old.executescript("""
            CREATE TABLE ciudades (id TEXT, lat_era5 REAL, lon_era5 REAL, elevacion_era5 REAL);
            CREATE TABLE descargas (id_ciudad TEXT, estado TEXT, fecha_inicio TEXT,
                                    fecha_fin TEXT, n_dias INTEGER, descargada_en TEXT);
            CREATE TABLE diario (id_ciudad TEXT, fecha TEXT, t_media REAL, t_max REAL,
                                 t_min REAL);
            INSERT INTO ciudades VALUES ('city-0', 40.0, -3.0, 600), ('other', 0, 0, 0);
            INSERT INTO descargas VALUES
                ('city-0', 'completa', '2024-01-01', '2024-01-02', 2, '2026-10-20'),
                ('city-1', 'pendiente', NULL, NULL, NULL, NULL),
                ('other', 'completa', '2024-01-01', '2024-01-02', 2, '2026-10-20');
            INSERT INTO diario VALUES ('city-0', '2024-01-01', 5, 10, 1),
                                      ('city-0', '2024-01-02', 6, 11, 2);
        """)

    assert import_clima_mundial(db, source) == 1  # 'other' is not in this project
    assert db.execute("SELECT COUNT(*) FROM daily").fetchone()[0] == 2
    assert db.execute(
        "SELECT status, n_days FROM downloads WHERE city_id = 'city-0'"
    ).fetchone() == ("complete", 2)
    assert db.execute(
        "SELECT era5_elevation FROM cities WHERE id = 'city-0'"
    ).fetchone() == (600.0,)
    assert import_clima_mundial(db, source) == 0  # already complete: nothing to do
