from datetime import date

import pytest
from pipelines import download
from pipelines.download import DownloadConfig, DownloadError, open_db
from pipelines.update import City, compare, complete_days, fetch_days

TODAY = date(2024, 2, 15)
MADRID = City("madrid-es", 40.0, -3.7, 40.5, -3.75, date(2024, 1, 31))
WINDOW = [
    f"2024-01-{day:02d}" for day in range(1, 32)
]  # the 30 days before the last date


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(download.time, "sleep", lambda seconds: None)


class FakeResponse:
    status_code = 200

    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


def response(times, latitude=40.5, t_mean=None, t_max=None, t_min=None):
    return {
        "latitude": latitude,
        "longitude": -3.75,
        "daily": {
            "time": times,
            "temperature_2m_mean": [5.0] * len(times) if t_mean is None else t_mean,
            "temperature_2m_max": [9.0] * len(times) if t_max is None else t_max,
            "temperature_2m_min": [1.0] * len(times) if t_min is None else t_min,
        },
    }


def fetch(body):
    requests_made = []

    def get(url, params, timeout):
        requests_made.append(params)
        return FakeResponse(body)

    usage = open_db(":memory:")
    days = fetch_days(usage, MADRID, TODAY, DownloadConfig(), lambda text: None, get)
    return days, requests_made[0]


def test_complete_days_stops_at_the_first_empty_value():
    # The real API gave this on 2026-11-05: a mean without maximum or minimum, then nothing
    daily = {
        "time": ["d1", "d2", "d3", "d4"],
        "temperature_2m_mean": [5.0, 6.0, 7.0, None],
        "temperature_2m_max": [9.0, 9.0, None, None],
        "temperature_2m_min": [1.0, 1.0, None, None],
    }
    assert complete_days(daily) == {
        "time": ["d1", "d2"],
        "temperature_2m_mean": [5.0, 6.0],
        "temperature_2m_max": [9.0, 9.0],
        "temperature_2m_min": [1.0, 1.0],
    }


def test_complete_days_without_data():
    assert complete_days({})["time"] == []


def test_fetch_asks_for_the_window_and_returns_complete_days():
    feb = ["2024-02-01", "2024-02-02"]
    times = [*WINDOW, *feb, "2024-02-03"]
    empty = len(times) - 1
    days, params = fetch(
        response(
            times,
            t_mean=[5.0] * empty + [None],
            t_max=[9.0] * empty + [None],
            t_min=[1.0] * empty + [None],
        )
    )
    assert (params["start_date"], params["end_date"]) == ("2024-01-01", "2024-02-15")
    assert params["models"] == "era5"
    assert (params["latitude"], params["longitude"]) == (40.0, -3.7)
    assert days[-1] == (date(2024, 2, 2), 5.0, 9.0, 1.0)
    assert len(days) == 33


def test_a_changed_era5_cell_is_rejected():
    with pytest.raises(DownloadError, match="cell changed"):
        fetch(response(WINDOW, latitude=40.75))


def test_a_response_without_complete_days_is_rejected():
    empty = [None] * len(WINDOW)
    with pytest.raises(DownloadError, match="no complete days"):
        fetch(response(WINDOW, t_mean=empty, t_max=empty, t_min=empty))


def test_a_gap_in_the_dates_is_rejected():
    with pytest.raises(DownloadError, match="dates"):
        fetch(response([d for d in WINDOW if d != "2024-01-10"]))


def test_impossible_temperatures_are_rejected():
    with pytest.raises(DownloadError, match="t_min"):
        fetch(response(WINDOW, t_mean=[20.0] * len(WINDOW)))


def test_compare_separates_new_changed_and_equal_days():
    d1, d2, d3 = date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)
    stored = {
        d1: (25.6000003, 32.700001, 16.9),  # how a 4-byte number can come back
        d2: (5.0, 9.0, 1.0),
    }
    changes = compare(
        [(d1, 25.6, 32.7, 16.9), (d2, 5.5, 9.0, 1.0), (d3, 7.0, 9.0, 1.0)], stored
    )
    assert changes.new == [(d3, 7.0, 9.0, 1.0)]
    assert changes.changed == [(d2, 5.5, 9.0, 1.0)]
    assert changes.largest_change == pytest.approx(0.5)
