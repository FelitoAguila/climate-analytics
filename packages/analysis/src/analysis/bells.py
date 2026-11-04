"""Distribution "bells": how the days of each year spread over the temperatures.

Instead of a histogram (a staircase that depends on where the bars are cut), each day puts a
small Gaussian bell of width `h` and area 1 at its temperature, and the bells are added up
(a kernel density estimate). The result is a smooth curve with the shape of the histogram.

Because every day adds area 1, the area under a year's curve is its number of days and the
height reads in **days per °C**: a peak of 160 at 26 °C means about 160 days of that year
were between 25.5 and 26.5 °C.
"""

import numpy as np
import pandas as pd

VARIABLES = [
    ("t_min", "Daily minima"),
    ("t_mean", "Daily means"),
    ("t_max", "Daily maxima"),
]
DAYS_PER_YEAR = 365


def silverman_bandwidth(values, n: int = DAYS_PER_YEAR) -> float:
    """Width `h` of each day's bell (Silverman's rule) for samples of `n` days.

    It is computed from every day of a city and used for all its years, so that the curves of
    different years can be compared.
    """
    values = np.asarray(values)
    spread = min(
        np.std(values), (np.percentile(values, 75) - np.percentile(values, 25)) / 1.34
    )
    return 0.9 * spread * n ** (-1 / 5)


def days_per_degree(values, axis: np.ndarray, h: float) -> np.ndarray:
    """Sum of one Gaussian bell of width h (and area 1) per day, evaluated at `axis`."""
    z = (axis[:, None] - np.asarray(values)[None, :]) / h
    return np.exp(-0.5 * z**2).sum(axis=1) / (h * np.sqrt(2 * np.pi))


def temperature_axis(city_daily: pd.DataFrame, points: int = 300) -> np.ndarray:
    """One axis for minima, means and maxima of a city.

    The margin beyond the coldest and the hottest day is 3 bell widths (the widest `h` of the
    three variables), and at least 5 % of the range: with less, the tail of the extreme days
    would be cut and the curve would lose area (Riyadh's maxima in the 2020s lost ~1.5 days
    with a plain 5 % margin).
    """
    low, high = city_daily["t_min"].min(), city_daily["t_max"].max()
    widest = max(silverman_bandwidth(city_daily[variable]) for variable, _ in VARIABLES)
    margin = max(0.05 * (high - low), 3 * widest)
    return np.linspace(low - margin, high + margin, points)


def curves_per_year(
    city_daily: pd.DataFrame, variable: str, axis: np.ndarray
) -> tuple[float, dict[int, np.ndarray]]:
    """The bell of each year for one variable of one city: (h, {year: curve})."""
    h = silverman_bandwidth(city_daily[variable])
    curves = {
        int(year): days_per_degree(group[variable], axis, h)
        for year, group in city_daily.groupby("year")
    }
    return h, curves


def decade_means(curves: dict[int, np.ndarray]) -> dict[int, np.ndarray]:
    """Mean curve of each decade ({1940: ..., 1950: ...}); the last one may be incomplete."""
    decades = sorted({year // 10 * 10 for year in curves})
    return {
        decade: np.mean(
            [curve for year, curve in curves.items() if decade <= year < decade + 10],
            axis=0,
        )
        for decade in decades
    }


def decade_label(decade: int, last_year: int) -> str:
    """'1940–1949', or '2020–2025' for an incomplete last decade."""
    return f"{decade}–{min(decade + 9, last_year)}"
