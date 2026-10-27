"""Plotly figure builders for the Austria Energy Intelligence dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


PRIMARY_BLUE = "#3C80A8"
DARK_BLUE = "#244F70"
LIGHT_BLUE = "#BFD7E5"
PALE_BLUE = "#E8F2F8"
BORDER_BLUE = "#B9CBD7"
MUTED_BLUE = "#6F8FA6"
WHITE = "#FFFFFF"


def _apply_corporate_layout(
    figure: go.Figure,
    *,
    title: str,
    y_axis_title: str,
    height: int = 420,
    hovermode: str = "closest",
) -> go.Figure:
    """Apply one accessible visual system to every dashboard figure."""

    figure.update_layout(
        title={
            "text": title,
            "x": 0.01,
            "xanchor": "left",
            "font": {"size": 18, "color": DARK_BLUE},
        },
        height=height,
        margin={"l": 58, "r": 24, "t": 64, "b": 52},
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        font={"family": "Arial, sans-serif", "size": 13, "color": DARK_BLUE},
        hovermode=hovermode,
        hoverlabel={"bgcolor": WHITE, "bordercolor": BORDER_BLUE, "font_color": DARK_BLUE},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"color": DARK_BLUE},
        },
        xaxis={
            "showline": True,
            "linecolor": BORDER_BLUE,
            "gridcolor": PALE_BLUE,
            "zeroline": False,
            "fixedrange": False,
        },
        yaxis={
            "title": y_axis_title,
            "showline": True,
            "linecolor": BORDER_BLUE,
            "gridcolor": PALE_BLUE,
            "zerolinecolor": BORDER_BLUE,
            "fixedrange": False,
            "tickformat": ",.0f",
        },
    )
    return figure


def monthly_trend_figure(trend: pd.DataFrame, rolling_window: int) -> go.Figure:
    """Build the monthly consumption and rolling-average trend figure."""

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=trend["month"],
            y=trend["consumption_gwh"],
            name="Monthly consumption",
            mode="lines+markers",
            line={"color": PRIMARY_BLUE, "width": 2.2},
            marker={"color": PRIMARY_BLUE, "size": 4, "opacity": 0.65},
            hovertemplate=(
                "<b>%{x|%b %Y}</b><br>Monthly consumption: %{y:,.1f} GWh"
                "<extra></extra>"
            ),
        )
    )

    rolling = trend.dropna(subset=["rolling_average_gwh"])
    if not rolling.empty:
        figure.add_trace(
            go.Scatter(
                x=rolling["month"],
                y=rolling["rolling_average_gwh"],
                name=f"{rolling_window}-month average",
                mode="lines",
                line={"color": DARK_BLUE, "width": 2.4, "dash": "dash"},
                hovertemplate=(
                    f"<b>%{{x|%b %Y}}</b><br>{rolling_window}-month average: "
                    "%{y:,.1f} GWh<extra></extra>"
                ),
            )
        )

    _apply_corporate_layout(
        figure,
        title="Monthly electricity consumption",
        y_axis_title="Consumption (GWh)",
        height=450,
        hovermode="x unified",
    )
    figure.update_xaxes(
        title=None,
        tickformat="%Y",
        nticks=10,
        rangeslider={
            "visible": True,
            "thickness": 0.07,
            "bgcolor": PALE_BLUE,
            "bordercolor": BORDER_BLUE,
            "borderwidth": 1,
        },
    )
    return figure


def seasonal_profile_figure(seasonal: pd.DataFrame) -> go.Figure:
    """Build a calendar-month seasonal profile from observed values."""

    custom_data = seasonal[["minimum_gwh", "maximum_gwh", "observations"]].to_numpy()
    figure = go.Figure(
        go.Scatter(
            x=seasonal["month_name"],
            y=seasonal["average_gwh"],
            customdata=custom_data,
            name="Historical monthly average",
            mode="lines+markers",
            line={"color": PRIMARY_BLUE, "width": 2.6},
            marker={
                "size": 9,
                "color": WHITE,
                "line": {"color": PRIMARY_BLUE, "width": 2.2},
            },
            hovertemplate=(
                "<b>%{x}</b><br>Average: %{y:,.1f} GWh"
                "<br>Observed minimum: %{customdata[0]:,.1f} GWh"
                "<br>Observed maximum: %{customdata[1]:,.1f} GWh"
                "<br>Observations: %{customdata[2]:.0f}<extra></extra>"
            ),
        )
    )
    _apply_corporate_layout(
        figure,
        title="Seasonal profile by calendar month",
        y_axis_title="Average consumption (GWh)",
        height=400,
    )
    figure.update_xaxes(title=None, categoryorder="array", categoryarray=seasonal["month_name"])
    minimum = float(seasonal["average_gwh"].min())
    maximum = float(seasonal["average_gwh"].max())
    padding = max((maximum - minimum) * 0.15, 150.0)
    figure.update_yaxes(range=[max(0.0, minimum - padding), maximum + padding])
    figure.update_layout(showlegend=False)
    return figure


def annual_totals_figure(annual: pd.DataFrame) -> go.Figure:
    """Build complete-calendar-year electricity consumption totals."""

    colors = [LIGHT_BLUE] * len(annual)
    if colors:
        colors[-1] = PRIMARY_BLUE

    figure = go.Figure(
        go.Bar(
            x=annual["year"],
            y=annual["consumption_twh"],
            marker={"color": colors, "line": {"color": PRIMARY_BLUE, "width": 1}},
            text=annual["consumption_twh"].map(lambda value: f"{value:.1f}"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Annual consumption: %{y:,.2f} TWh<extra></extra>",
            name="Annual consumption",
        )
    )
    _apply_corporate_layout(
        figure,
        title="Annual consumption — complete years",
        y_axis_title="Consumption (TWh)",
        height=410,
    )
    figure.update_xaxes(title=None, dtick=1, type="linear")
    figure.update_yaxes(rangemode="tozero", tickformat=",.0f")
    figure.update_layout(showlegend=False)
    return figure


def annual_yoy_figure(annual: pd.DataFrame) -> go.Figure:
    """Build neutral-color annual year-over-year growth bars."""

    growth = annual.dropna(subset=["yoy_pct"]).copy()
    colors = [PRIMARY_BLUE if value >= 0 else MUTED_BLUE for value in growth["yoy_pct"]]
    labels = [f"{value:+.1f}%" for value in growth["yoy_pct"]]

    figure = go.Figure(
        go.Bar(
            x=growth["year"],
            y=growth["yoy_pct"],
            marker={"color": colors, "line": {"color": DARK_BLUE, "width": 0.7}},
            text=labels,
            textposition="outside",
            cliponaxis=False,
            customdata=growth["consumption_twh"],
            hovertemplate=(
                "<b>%{x}</b><br>Change vs prior complete year: %{y:+.2f}%"
                "<br>Annual consumption: %{customdata:,.2f} TWh<extra></extra>"
            ),
            name="Annual YoY change",
        )
    )
    _apply_corporate_layout(
        figure,
        title="Year-over-year growth — complete years",
        y_axis_title="Change (%)",
        height=410,
    )
    figure.update_xaxes(title=None, dtick=1, type="linear")
    figure.update_yaxes(ticksuffix="%", tickformat="+.1f", zeroline=True, zerolinewidth=1.2)
    figure.update_layout(showlegend=False)
    return figure
