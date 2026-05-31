"""Plotly chart factory functions for the Streamlit dashboard."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative

logger = logging.getLogger(__name__)

_DARK_TEMPLATE = "plotly_dark"
_NO_DATA_MESSAGE = "No data available"


def _empty_figure(title: str, x_title: str = "", y_title: str = "") -> go.Figure:
    """Build an empty figure with a standard no-data annotation.

    Args:
        title: Chart title to display.
        x_title: X-axis label.
        y_title: Y-axis label.

    Returns:
        A Plotly figure containing a no-data annotation.
    """

    figure = go.Figure()
    figure.update_layout(
        template=_DARK_TEMPLATE,
        title=title,
        autosize=True,
        xaxis_title=x_title,
        yaxis_title=y_title,
        annotations=[
            {
                "text": _NO_DATA_MESSAGE,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 16},
            }
        ],
    )
    return figure


def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a defensive copy with normalized columns.

    Args:
        df: Input DataFrame.

    Returns:
        A copied DataFrame safe for chart transformations.
    """

    return df.copy(deep=True) if not df.empty else df.copy()


def bar_top_authors(df: pd.DataFrame) -> go.Figure:
    """Build a horizontal bar chart for top authors.

    Args:
        df: DataFrame with ``author_name``, ``message_count``, and ``avg_content_length`` columns.

    Returns:
        A Plotly figure containing the horizontal bar chart.
    """

    title = "Top Active Users by Message Count"
    if df.empty:
        return _empty_figure(title, "Message Count", "Author")

    frame = _prepare_dataframe(df)
    frame = frame.sort_values("message_count", ascending=True)

    figure = go.Figure(
        go.Bar(
            x=frame["message_count"],
            y=frame["author_name"],
            orientation="h",
            marker={
                "color": frame["message_count"],
                "colorscale": "Blues",
                "showscale": True,
            },
            customdata=frame[["author_name", "message_count", "avg_content_length"]].to_numpy(),
            hovertemplate=(
                "Author: %{customdata[0]}<br>"
                "Messages: %{customdata[1]}<br>"
                "Avg. Content Length: %{customdata[2]:.2f}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        template=_DARK_TEMPLATE,
        title=title,
        autosize=True,
        xaxis_title="Message Count",
        yaxis_title="Author",
    )
    return figure


def line_activity_trend(df: pd.DataFrame) -> go.Figure:
    """Build a line chart with rolling average for daily activity.

    Args:
        df: DataFrame with ``date`` and ``message_count`` columns.

    Returns:
        A Plotly figure containing the activity trend chart.
    """

    title = "Daily Message Activity"
    if df.empty:
        return _empty_figure(title, "Date", "Message Count")

    frame = _prepare_dataframe(df)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["message_count"] = pd.to_numeric(frame["message_count"], errors="coerce").fillna(0)
    frame = frame.dropna(subset=["date"]).sort_values("date")
    frame["rolling_average"] = frame["message_count"].rolling(window=7, min_periods=1).mean()

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=frame["date"],
            y=frame["message_count"],
            mode="lines",
            name="Messages",
            line={"shape": "spline", "width": 3},
            fill="tozeroy",
            fillcolor="rgba(31, 119, 180, 0.25)",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=frame["date"],
            y=frame["rolling_average"],
            mode="lines",
            name="7-Day Rolling Average",
            line={"shape": "spline", "dash": "dash", "width": 2},
        )
    )
    figure.update_layout(
        template=_DARK_TEMPLATE,
        title=title,
        autosize=True,
        xaxis_title="Date",
        yaxis_title="Message Count",
    )
    return figure


def bar_channel_breakdown(df: pd.DataFrame) -> go.Figure:
    """Build a vertical bar chart showing channel message counts.

    Args:
        df: DataFrame with ``channel_name`` and ``message_count`` columns.

    Returns:
        A Plotly figure containing the channel breakdown bar chart.
    """

    title = "Messages per Channel"
    if df.empty:
        return _empty_figure(title, "Channel", "Message Count")

    frame = _prepare_dataframe(df).sort_values("message_count", ascending=False)

    figure = go.Figure()
    palette = qualitative.Plotly

    for index, row in enumerate(frame.itertuples(index=False)):
        figure.add_trace(
            go.Bar(
                x=[row.channel_name],
                y=[row.message_count],
                name=row.channel_name,
                marker_color=palette[index % len(palette)],
            )
        )

    figure.update_layout(
        template=_DARK_TEMPLATE,
        title=title,
        autosize=True,
        xaxis_title="Channel",
        yaxis_title="Message Count",
    )
    return figure


def pie_channel_share(df: pd.DataFrame) -> go.Figure:
    """Build a donut chart showing channel share of total messages.

    Args:
        df: DataFrame with ``channel_name`` and ``share_pct`` columns.

    Returns:
        A Plotly figure containing the donut pie chart.
    """

    title = "Channel Share of Total Messages"
    if df.empty:
        return _empty_figure(title)

    frame = _prepare_dataframe(df)
    figure = go.Figure(
        go.Pie(
            labels=frame["channel_name"],
            values=frame["share_pct"],
            hole=0.4,
            textinfo="label+percent",
        )
    )
    figure.update_layout(template=_DARK_TEMPLATE, title=title, autosize=True)
    return figure


def line_member_growth(df: pd.DataFrame) -> go.Figure:
    """Build a member growth chart with join, leave, and net change traces.

    Args:
        df: DataFrame with ``date``, ``joins``, ``leaves``, and ``net_change`` columns.

    Returns:
        A Plotly figure containing the member growth chart.
    """

    title = "Member Join/Leave Activity"
    if df.empty:
        return _empty_figure(title, "Date", "Member Events")

    frame = _prepare_dataframe(df)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame[["joins", "leaves", "net_change"]] = frame[["joins", "leaves", "net_change"]].apply(
        pd.to_numeric,
        errors="coerce",
    ).fillna(0)
    frame = frame.dropna(subset=["date"]).sort_values("date")

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=frame["date"],
            y=frame["joins"],
            name="Joins",
            marker_color="green",
        )
    )
    figure.add_trace(
        go.Bar(
            x=frame["date"],
            y=frame["leaves"],
            name="Leaves",
            marker_color="red",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=frame["date"],
            y=frame["net_change"],
            name="Net Change",
            mode="lines+markers",
            line={"color": "deepskyblue", "width": 3},
        )
    )
    figure.update_layout(
        template=_DARK_TEMPLATE,
        title=title,
        autosize=True,
        xaxis_title="Date",
        yaxis_title="Count",
        barmode="group",
    )
    return figure


def heatmap_activity(df: pd.DataFrame) -> go.Figure:
    """Build a heatmap of activity by hour and day of week.

    Args:
        df: DataFrame with ``hour``, ``day_of_week``, and ``message_count`` columns.

    Returns:
        A Plotly figure containing the activity heatmap.
    """

    title = "Message Activity Heatmap (Hour × Day)"
    if df.empty:
        return _empty_figure(title, "Hour", "Day of Week")

    frame = _prepare_dataframe(df)
    frame["hour"] = pd.to_numeric(frame["hour"], errors="coerce").fillna(0).astype(int)
    frame["day_of_week"] = pd.to_numeric(frame["day_of_week"], errors="coerce").fillna(0).astype(int)
    frame["message_count"] = pd.to_numeric(frame["message_count"], errors="coerce").fillna(0)

    pivot = frame.pivot_table(index="day_of_week", columns="hour", values="message_count", aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(index=list(range(7)), columns=list(range(24)), fill_value=0)
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    figure = go.Figure(
        go.Heatmap(
            z=pivot.to_numpy(),
            x=list(pivot.columns),
            y=day_labels,
            colorscale="YlOrRd",
            colorbar={"title": "Messages"},
        )
    )
    figure.update_layout(
        template=_DARK_TEMPLATE,
        title=title,
        autosize=True,
        xaxis_title="Hour",
        yaxis_title="Day of Week",
    )
    return figure