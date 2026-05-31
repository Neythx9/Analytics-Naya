"""Users page for the Streamlit dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components import ExportManager, bar_top_authors


def render(df: pd.DataFrame, export_manager: ExportManager, guild_id: str, days: int) -> None:
    """Render the users analytics page.

    Args:
        df: DataFrame containing top author analytics.
        export_manager: Export helper for CSV downloads.
        guild_id: Discord guild identifier.
        days: Rolling window size in days.

    Returns:
        None.
    """

    fig = bar_top_authors(df)
    st.plotly_chart(fig, use_container_width=True)
    filename = export_manager.generate_filename("top_users", guild_id, days)
    export_manager.get_export_button(df, "Download Top Users", filename)