"""Charts of the annual statistics (matplotlib). Each function returns the figure."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
