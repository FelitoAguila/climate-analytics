"""City map callbacks: map theme, year bounds and annual distributions."""

from __future__ import annotations

from dash import Input, Output, no_update

from ..components.distributions import (
    VARIABLES,
    build_distribution_figure,
    empty_distribution_figure,
    year_marks,
)
from ..components.maps import MAP_ID, map_theme_patch
from ..data import DataUnavailable, city_daily, get_city


def _is_map_path(pathname: str | None) -> bool:
    return (pathname or "").rstrip("/") == "/map"


def _city_title(city_id: str) -> str:
    try:
        city = get_city(city_id)
    except DataUnavailable:
        return city_id
    if not city:
        return city_id
    name = city.get("name") or city_id
    country = city.get("country")
    return f"{name} ({country})" if country else str(name)


def _available_years(frame) -> tuple[int, int] | None:
    years = frame["date"].dt.year.dropna()
    if years.empty:
        return None
    return int(years.min()), int(years.max())


def year_range_response(city_id):
    """Return slider bounds for the selected city."""
    if not city_id:
        return no_update, no_update, no_update, no_update, True

    try:
        frame = city_daily(city_id)
    except DataUnavailable:
        return no_update, no_update, no_update, no_update, True

    bounds = _available_years(frame)
    if bounds is None:
        return no_update, no_update, no_update, no_update, True

    start_year, end_year = bounds
    return (
        start_year,
        end_year,
        [start_year, end_year],
        year_marks(start_year, end_year),
        False,
    )


def distribution_response(city_id, variable, year_range, theme):
    """Build the distribution chart, city title and status line."""
    variable = variable if variable in VARIABLES else "t_mean"

    if not city_id:
        return (
            empty_distribution_figure(theme),
            "Select a city",
            "Choose a city to load its annual distributions.",
        )

    title = _city_title(city_id)
    try:
        frame = city_daily(city_id)
    except DataUnavailable:
        return (
            empty_distribution_figure(
                theme, "The daily records could not be loaded right now."
            ),
            title,
            "The daily records could not be loaded. Please try again shortly.",
        )

    if frame.empty:
        return (
            empty_distribution_figure(
                theme, "No daily records are available for this city."
            ),
            title,
            "No daily records available for this city.",
        )

    bounds = _available_years(frame)
    if bounds is None:
        return (
            empty_distribution_figure(theme, "No dates are available for this city."),
            title,
            "No dates available for this city.",
        )

    if year_range and year_range[0] is not None and year_range[1] is not None:
        start_year, end_year = int(year_range[0]), int(year_range[1])
    else:
        start_year, end_year = bounds

    figure, included_years = build_distribution_figure(
        frame,
        variable,
        start_year,
        end_year,
        theme,
    )
    if not included_years:
        return (
            figure,
            title,
            f"No {VARIABLES[variable].lower()} data in {start_year}–{end_year}.",
        )

    unit = "year" if len(included_years) == 1 else "years"
    status = (
        f"{VARIABLES[variable]} · {start_year}–{end_year} · "
        f"{len(included_years)} {unit}"
    )
    return figure, title, status


def register(app) -> None:
    @app.callback(
        Output(MAP_ID, "figure"),
        Input("theme-store", "data"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )
    def sync_map_theme(theme, pathname):
        if not _is_map_path(pathname):
            return no_update
        return map_theme_patch(theme)

    @app.callback(
        Output("year-range", "min"),
        Output("year-range", "max"),
        Output("year-range", "value"),
        Output("year-range", "marks"),
        Output("year-range", "disabled"),
        Input("city-filter", "value"),
        prevent_initial_call=False,
    )
    def update_year_range(city_id):
        return year_range_response(city_id)

    @app.callback(
        Output("distribution-chart", "figure"),
        Output("distribution-city", "children"),
        Output("distribution-status", "children"),
        Input("city-filter", "value"),
        Input("temperature-variable", "value"),
        Input("year-range", "value"),
        Input("theme-store", "data"),
        prevent_initial_call=False,
    )
    def update_distribution(city_id, variable, year_range, theme):
        return distribution_response(city_id, variable, year_range, theme)
