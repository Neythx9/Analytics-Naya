"""Trends page for the Streamlit dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components import ExportManager, heatmap_activity, line_activity_trend, line_member_growth


def render(
    activity_df: pd.DataFrame,
    growth_df: pd.DataFrame,
    heatmap_df: pd.DataFrame,
    export_manager: ExportManager,
    guild_id: str,
    days: int,
) -> None:
    """Render the trends analytics page.

    Args:
        activity_df: DataFrame for the activity trend chart.
        growth_df: DataFrame for the member growth chart.
        heatmap_df: DataFrame for the activity heatmap chart.
        export_manager: Export helper for CSV downloads.
        guild_id: Discord guild identifier.
        days: Rolling window size in days.

    Returns:
        None.
    """

    st.plotly_chart(line_activity_trend(activity_df), use_container_width=True)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(line_member_growth(growth_df), use_container_width=True)
    with right:
        st.plotly_chart(heatmap_activity(heatmap_df), use_container_width=True)

    export_left, export_right = st.columns(2)
    with export_left:
        filename = export_manager.generate_filename("message_trend", guild_id, days)
        export_manager.get_export_button(activity_df, "Download Message Trend", filename)
    with export_right:
        filename = export_manager.generate_filename("member_growth", guild_id, days)
        export_manager.get_export_button(growth_df, "Download Member Growth", filename)