"""Channels page for the Streamlit dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components import ExportManager, bar_channel_breakdown, pie_channel_share


def render(breakdown_df: pd.DataFrame, share_df: pd.DataFrame, export_manager: ExportManager, guild_id: str, days: int) -> None:
    """Render the channels analytics page.

    Args:
        breakdown_df: DataFrame for the channel breakdown bar chart.
        share_df: DataFrame for the channel share donut chart.
        export_manager: Export helper for CSV downloads.
        guild_id: Discord guild identifier.
        days: Rolling window size in days.

    Returns:
        None.
    """

    left, right = st.columns([2, 1])
    with left:
        st.plotly_chart(bar_channel_breakdown(breakdown_df), use_container_width=True)
    with right:
        st.plotly_chart(pie_channel_share(share_df), use_container_width=True)

    filename = export_manager.generate_filename("channel_breakdown", guild_id, days)
    export_manager.get_export_button(breakdown_df, "Download Channel Breakdown", filename)