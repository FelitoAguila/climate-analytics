"""Interactive world map of all cities in the dataset."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from dash import Patch

MAP_ID = "city-map"
_MARKER_SIZE = 9

_CONTINENT_COLORS = {
    "Africa": "#e67e22",
    "Antarctica": "#95a5a6",
    "Asia": "#e74c3c",
    "Europe": "#3498db",
    "North America": "#2ecc71",
    "Oceania": "#f1c40f",
    "South America": "#9b59b6",
    "Unknown": "#7f8c8d",
}

_LIGHT = {
    "land": "#eef2f5",
    "ocean": "#dcecf1",
    "country": "#c7d0d8",
    "coastline": "#aebac4",
    "text": "#2f3742",
    "hover_bg": "#ffffff",
    "border": "#d7dde4",
    "legend_bg": "rgba(255, 255, 255, 0.88)",
}

_DARK = {
    "land": "#232a34",
    "ocean": "#16222c",
    "country": "#35404d",
    "coastline": "#4a5866",
    "text": "#e5e8ec",
    "hover_bg": "#1c2027",
    "border": "#3a4350",
    "legend_bg": "rgba(28, 32, 39, 0.9)",
}


def map_colors(theme: str | None) -> dict[str, str]:
    """Return the map palette for the requested theme."""
    return (_DARK if theme == "dark" else _LIGHT).copy()


def _text(value: Any, default: str = "—") -> str:
    if value is None:
        return default
    try:
        if bool(pd.isna(value)):
            return default
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or default


def _hover_text(row: Any) -> str:
    return f"<b>{_text(row.name)}</b><br>{_text(row.country)} · {_text(row.continent)}"


def build_city_map(cities: pd.DataFrame, theme: str | None = "light") -> go.Figure:
    """Build the Scattergeo figure showing every city."""
    colors = map_colors(theme)
    fig = go.Figure()

    frame = cities.loc[cities["latitude"].notna() & cities["longitude"].notna()].copy()
    frame = frame.reset_index(drop=True)

    if not frame.empty:
        frame["continent"] = frame["continent"].fillna("Unknown")
        hover = [_hover_text(row) for row in frame.itertuples(index=False)]

        for continent, group in frame.groupby("continent", sort=True):
            fig.add_trace(
                go.Scattergeo(
                    lat=group["latitude"],
                    lon=group["longitude"],
                    name=str(continent),
                    text=group["name"],
                    customdata=group["id"],
                    mode="markers",
                    marker={
                        "size": _MARKER_SIZE,
                        "color": _CONTINENT_COLORS.get(
                            continent, _CONTINENT_COLORS["Unknown"]
                        ),
                        "line": {"width": 1, "color": "#ffffff"},
                        "opacity": 0.88,
                    },
                    hovertext=[hover[index] for index in group.index],
                    hovertemplate="%{hovertext}<extra></extra>",
                )
            )
    else:
        fig.add_annotation(
            text="No cities with coordinates available.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"color": colors["text"], "size": 13},
        )

    fig.update_geos(
        projection_type="natural earth",
        showland=True,
        landcolor=colors["land"],
        showocean=True,
        oceancolor=colors["ocean"],
        showlakes=False,
        showcountries=True,
        countrycolor=colors["country"],
        countrywidth=0.5,
        showcoastlines=True,
        coastlinecolor=colors["coastline"],
        coastlinewidth=0.7,
        bgcolor="rgba(0, 0, 0, 0)",
        showframe=False,
    )
    fig.update_layout(
        autosize=True,
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        dragmode="pan",
        hovermode="closest",
        uirevision=MAP_ID,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 0.01,
            "xanchor": "left",
            "x": 0.01,
            "bgcolor": colors["legend_bg"],
            "font": {"color": colors["text"], "size": 11},
        },
        hoverlabel={
            "bgcolor": colors["hover_bg"],
            "bordercolor": colors["border"],
            "font": {"color": colors["text"], "size": 12},
            "align": "left",
        },
    )
    return fig


def map_theme_patch(theme: str | None) -> Patch:
    """Return a Dash patch that switches the map colours without rebuilding it."""
    colors = map_colors(theme)
    patch = Patch()
    patch["layout"]["geo"]["landcolor"] = colors["land"]
    patch["layout"]["geo"]["oceancolor"] = colors["ocean"]
    patch["layout"]["geo"]["countrycolor"] = colors["country"]
    patch["layout"]["geo"]["coastlinecolor"] = colors["coastline"]
    patch["layout"]["legend"]["font"]["color"] = colors["text"]
    patch["layout"]["legend"]["bgcolor"] = colors["legend_bg"]
    patch["layout"]["hoverlabel"]["bgcolor"] = colors["hover_bg"]
    patch["layout"]["hoverlabel"]["bordercolor"] = colors["border"]
    patch["layout"]["hoverlabel"]["font"]["color"] = colors["text"]
    return patch
