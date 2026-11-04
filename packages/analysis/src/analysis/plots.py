"""Charts of the annual statistics and of the bells (matplotlib).

Each function returns the figure.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.bells import (
    VARIABLES,
    curves_per_year,
    decade_label,
    decade_means,
    temperature_axis,
)
from analysis.stats import (
    LESS_RELIABLE_BEFORE,
    RECENT_TREND_FROM,
    RECENT_YEARS,
    REFERENCE,
)


def plot_annual_means(
    annual: pd.DataFrame,
    summary: pd.DataFrame,
    city_id: str,
    title: str | None = None,
) -> plt.Figure:
    """Annual means of the maxima (red), the means (black) and the minima (blue) of a city.

    The dashed line is the trend of the mean since 1975 and the light blue band, the reference
    period 1961–1990. If the blue line rises more than the red one, nights warm faster than days.
    """
    table = annual.loc[city_id]
    s = summary.loc[city_id]
    years = table.index.to_numpy()

    fig, ax = plt.subplots(figsize=(11, 5))
    lines = [
        ("max_mean", "mean of the maxima", "tab:red"),
        ("mean", "mean", "black"),
        ("min_mean", "mean of the minima", "tab:blue"),
    ]
    for column, label, color in lines:
        ax.plot(
            years,
            table[column],
            color=color,
            linewidth=1.5,
            marker="o",
            markersize=2.5,
            label=label,
        )
        # Label at the end of each line, so there is no need to look at the legend
        ax.annotate(
            f"{table[column].iloc[-1]:.1f} °C",
            (years[-1], table[column].iloc[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
            color=color,
        )

    since = years >= RECENT_TREND_FROM
    line = np.polyval(
        np.polyfit(years[since], table["mean"].to_numpy()[since], 1), years[since]
    )
    ax.plot(
        years[since],
        line,
        color="black",
        linestyle="--",
        linewidth=1,
        label=f"trend since {RECENT_TREND_FROM}: {s['recent_trend']:+.2f} °C/decade",
    )
    ax.axvspan(
        REFERENCE[0],
        REFERENCE[1],
        color="tab:blue",
        alpha=0.07,
        label=f"reference {REFERENCE[0]}–{REFERENCE[1]}",
    )
    ax.axvspan(
        years[0] - 0.5,
        LESS_RELIABLE_BEFORE - 0.5,
        color="grey",
        alpha=0.15,
        label=f"before {LESS_RELIABLE_BEFORE}: less reliable",
    )

    ax.set_xlim(years[0] - 1, years[-1] + 8)  # room on the right for the labels
    ax.set_ylabel("Temperature (°C)")
    ax.set_title(
        f"{title or city_id} · annual mean temperatures {years[0]}–{years[-1]}\n"
        f"{years[-1] - RECENT_YEARS + 1}–{years[-1]}: {s['difference']:+.2f} °C "
        f"compared with {REFERENCE[0]}–{REFERENCE[1]}"
    )
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def plot_bells(
    daily: pd.DataFrame, city_id: str, title: str | None = None
) -> plt.Figure:
    """The bell of every year of a city: minima, means and maxima, one curve per year.

    Colour = year, from blue (1940) to red (last year). Thin curves are single years; thick
    ones, the mean of each decade. If the city warms, the red curves sit to the right of the
    blue ones. The three panels share the temperature axis.
    """
    city_daily = daily[daily["city_id"] == city_id]
    years = np.sort(city_daily["year"].unique())
    colours = plt.get_cmap("coolwarm")
    normalize = plt.Normalize(years[0], years[-1])
    axis = temperature_axis(city_daily)

    fig, axes = plt.subplots(3, 1, figsize=(11, 11), sharex=True)
    for ax, (variable, name) in zip(axes, VARIABLES):
        h, curves = curves_per_year(city_daily, variable, axis)
        for year, curve in curves.items():
            ax.plot(
                axis, curve, color=colours(normalize(year)), linewidth=0.6, alpha=0.35
            )
        # Mean of each decade, thick with a white border so it stands out
        for decade, curve in decade_means(curves).items():
            ax.plot(axis, curve, color="white", linewidth=3.6)
            ax.plot(axis, curve, color=colours(normalize(decade + 4.5)), linewidth=2.2)
        ax.set_title(f"{name} · width h = {h:.2f} °C", fontsize=10, loc="left")
        ax.set_ylabel("Days per °C")
        ax.grid(alpha=0.3)

    axes[0].plot([], [], color="grey", linewidth=0.6, label="one year")
    axes[0].plot([], [], color="grey", linewidth=2.2, label="mean of the decade")
    axes[0].legend(loc="upper left", fontsize=8)
    bar = fig.colorbar(
        plt.cm.ScalarMappable(norm=normalize, cmap=colours),
        ax=axes,
        fraction=0.03,
        pad=0.02,
    )
    bar.set_label("Year")
    axes[-1].set_xlabel("Temperature (°C)")
    fig.suptitle(
        f"{title or city_id} · distribution of the daily temperatures of each year, "
        f"{years[0]}–{years[-1]}",
        fontsize=12,
    )
    return fig


def plot_decade_bells(
    daily: pd.DataFrame, city_id: str, title: str | None = None
) -> plt.Figure:
    """Only the mean bell of each decade, side by side for minima, means and maxima."""
    city_daily = daily[daily["city_id"] == city_id]
    axis = temperature_axis(city_daily)
    last_year = int(city_daily["year"].max())
    colours = plt.get_cmap("coolwarm")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharex=True)
    for ax, (variable, name) in zip(axes, VARIABLES):
        _, curves = curves_per_year(city_daily, variable, axis)
        decades = decade_means(curves)
        for i, (decade, curve) in enumerate(decades.items()):
            ax.plot(
                axis,
                curve,
                color=colours(i / max(len(decades) - 1, 1)),
                linewidth=1.8,
                label=decade_label(decade, last_year),
            )
        ax.set_title(name, fontsize=10)
        ax.set_xlabel("Temperature (°C)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Days per °C")
    axes[-1].legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1))
    fig.suptitle(f"{title or city_id} · bells per decade", fontsize=12)
    fig.tight_layout()
    return fig


def plot_bells_comparison(
    daily: pd.DataFrame,
    city_ids: list[str],
    titles: dict[str, str] | None = None,
    variable: str = "t_mean",
    columns: int = 3,
) -> plt.Figure:
    """Decade bells of several cities, one panel each, for one variable.

    Each panel has its own temperature axis, because climates are very different: compare how
    the curves move from blue to red, not where they are.
    """
    titles = titles or {}
    rows = -(-len(city_ids) // columns)  # division rounding up
    fig, axes = plt.subplots(rows, columns, figsize=(15, 3.8 * rows), squeeze=False)
    colours = plt.get_cmap("coolwarm")
    for ax, city_id in zip(axes.flat, city_ids):
        city_daily = daily[daily["city_id"] == city_id]
        axis = temperature_axis(city_daily)
        decades = decade_means(curves_per_year(city_daily, variable, axis)[1])
        for i, curve in enumerate(decades.values()):
            ax.plot(
                axis, curve, color=colours(i / max(len(decades) - 1, 1)), linewidth=1.5
            )
        ax.set_title(titles.get(city_id, city_id), fontsize=10)
        ax.grid(alpha=0.3)
    for ax in axes.flat[len(city_ids) :]:
        ax.set_visible(False)  # spare panels of the last row
    for ax in axes[:, 0]:
        ax.set_ylabel("Days per °C")
    name = dict(VARIABLES)[variable].lower()
    fig.suptitle(
        f"Bells per decade of the {name} · blue 1940s → red 2020s", fontsize=12
    )
    fig.tight_layout()
    return fig
