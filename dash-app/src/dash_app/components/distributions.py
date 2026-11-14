"""Annual temperature distributions as a Plotly ridge plot."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.colors as pc
import plotly.graph_objects as go

VARIABLES = {
    "t_mean": "Mean temperature",
    "t_min": "Minimum temperature",
    "t_max": "Maximum temperature",
}

_YEAR_COLORS = [
    "#2c7bb6",
    "#74add1",
    "#abd9e9",
    "#ffffbf",
    "#fdae61",
    "#f46d43",
    "#d73027",
]

_CHART_LIGHT = {
    "text": "#2f3742",
    "grid": "#e6e9ee",
    "line": "#c7d0d8",
    "hover_bg": "#ffffff",
    "border": "#d7dde4",
}

_CHART_DARK = {
    "text": "#e5e8ec",
    "grid": "#2b303a",
    "line": "#3a4350",
    "hover_bg": "#1c2027",
    "border": "#3a4350",
}

_RIDGE_HEIGHT = 0.85
_GRID_POINTS = 256


def distribution_theme(theme: str | None) -> dict[str, str]:
    """Return chart colours for the requested theme."""
    return (_CHART_DARK if theme == "dark" else _CHART_LIGHT).copy()


def year_marks(start_year: int, end_year: int) -> dict[int, str]:
    """Build readable year ticks for the range slider and ridge axis."""
    if end_year < start_year:
        start_year, end_year = end_year, start_year
    span = max(0, end_year - start_year)
    step = 10 if span > 40 else 5 if span > 15 else 1
    years = list(range(start_year, end_year + 1, step))
    if years[-1] != end_year:
        years.append(end_year)
    return {year: str(year) for year in years}


def _rgba(color: str, alpha: float) -> str:
    if color.startswith("rgb("):
        return f"rgba({color[4:-1]}, {alpha})"
    return color


def _year_color(year: int, first_year: int, last_year: int) -> str:
    position = (
        0.5
        if last_year <= first_year
        else (year - first_year) / (last_year - first_year)
    )
    return pc.sample_colorscale(_YEAR_COLORS, [position])[0]


def _kde(values: np.ndarray, grid: np.ndarray) -> np.ndarray | None:
    count = values.size
    if count < 2:
        return None

    std = float(np.std(values, ddof=1))
    q75, q25 = np.percentile(values, [75, 25])
    iqr = float(q75 - q25)
    spread = min(std, iqr / 1.34) if iqr > 0 else std
    if not np.isfinite(spread) or spread <= 0:
        spread = std if np.isfinite(std) and std > 0 else 1.0

    bandwidth = 0.9 * spread * count ** (-0.2)
    if bandwidth <= 0:
        return None

    z = (grid[:, None] - values[None, :]) / bandwidth
    density = np.exp(-0.5 * z * z).sum(axis=1)
    density /= count * bandwidth * np.sqrt(2 * np.pi)
    return density


def empty_distribution_figure(
    theme: str | None = "light",
    message: str = "Choose a city to see its annual temperature distributions.",
) -> go.Figure:
    """Return a placeholder or error figure."""
    colors = distribution_theme(theme)
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"color": colors["text"], "size": 14},
    )
    figure.update_layout(
        height=360,
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return figure


def build_distribution_figure(
    frame: pd.DataFrame,
    variable: str,
    start_year: int,
    end_year: int,
    theme: str | None = "light",
) -> tuple[go.Figure, list[int]]:
    """Build a ridge plot with one KDE curve per year."""
    colors = distribution_theme(theme)
    variable = variable if variable in VARIABLES else "t_mean"
    label = VARIABLES[variable]

    years = frame["date"].dt.year
    selected = frame.loc[years.between(start_year, end_year)]
    if selected.empty:
        return empty_distribution_figure(theme, "No data in this year range."), []

    values_by_year: dict[int, np.ndarray] = {}
    for year, group in selected.groupby(selected["date"].dt.year, sort=True):
        values = pd.to_numeric(group[variable], errors="coerce").to_numpy(dtype=float)
        values = values[np.isfinite(values)]
        if values.size >= 2:
            values_by_year[int(year)] = values

    if not values_by_year:
        return (
            empty_distribution_figure(
                theme, "No valid daily values for this selection."
            ),
            [],
        )

    included_years = sorted(values_by_year)
    all_values = np.concatenate(list(values_by_year.values()))
    low = float(all_values.min())
    high = float(all_values.max())
    if high <= low:
        low -= 1.0
        high += 1.0
    padding = max(0.5, (high - low) * 0.05)
    grid = np.linspace(low - padding, high + padding, _GRID_POINTS)

    figure = go.Figure()
    first_year = included_years[0]
    last_year = included_years[-1]

    for year in included_years:
        density = _kde(values_by_year[year], grid)
        if density is None or density.max() <= 0:
            continue
        ridge = density / density.max() * _RIDGE_HEIGHT
        color = _year_color(year, first_year, last_year)
        x_values = np.concatenate(([grid[0]], grid, [grid[-1]]))
        y_values = np.concatenate(([year], year + ridge, [year]))
        figure.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines",
                fill="toself",
                fillcolor=_rgba(color, 0.55),
                line={"width": 0},
                hoverinfo="skip",
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=grid,
                y=year + ridge,
                mode="lines",
                name=str(year),
                line={"color": color, "width": 1.1},
                hovertemplate=f"<b>{year}</b><br>%{{x:.1f}} °C<extra></extra>",
                showlegend=False,
            )
        )

    if not figure.data:
        return (
            empty_distribution_figure(
                theme, "No usable distributions for this selection."
            ),
            [],
        )

    ticks = sorted(year_marks(first_year, last_year))
    height = max(520, min(2600, 16 * len(included_years) + 140))
    figure.update_layout(
        height=height,
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font={"color": colors["text"], "size": 12},
        margin={"l": 70, "r": 24, "t": 20, "b": 56},
        hovermode="closest",
        dragmode="pan",
        xaxis={
            "title": {"text": f"{label} (°C)", "font": {"color": colors["text"]}},
            "gridcolor": colors["grid"],
            "zerolinecolor": colors["line"],
            "linecolor": colors["line"],
            "tickfont": {"color": colors["text"]},
        },
        yaxis={
            "title": {"text": "Year", "font": {"color": colors["text"]}},
            "tickmode": "array",
            "tickvals": ticks,
            "ticktext": [str(year) for year in ticks],
            "range": [first_year - 0.6, last_year + _RIDGE_HEIGHT + 0.6],
            "gridcolor": colors["grid"],
            "zeroline": False,
            "linecolor": colors["line"],
            "tickfont": {"color": colors["text"]},
        },
        hoverlabel={
            "bgcolor": colors["hover_bg"],
            "bordercolor": colors["border"],
            "font": {"color": colors["text"], "size": 12},
        },
    )
    return figure, included_years
