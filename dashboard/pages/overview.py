"""Overview page for the Streamlit dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.components import ExportManager, line_activity_trend


def render(
    kpis: dict[str, Any],
    activity_df: pd.DataFrame,
    top_users_df: pd.DataFrame,
    channel_breakdown_df: pd.DataFrame,
    member_events_df: pd.DataFrame,
    export_manager: ExportManager,
    guild_id: str,
    days: int,
) -> None:
    """Render the overview dashboard page.

    Args:
        kpis: Dictionary containing KPI values.
        activity_df: DataFrame for the seven-day activity sparkline.
        top_users_df: DataFrame containing top user analytics.
        channel_breakdown_df: DataFrame containing channel analytics.
        member_events_df: DataFrame containing member event analytics.
        export_manager: Export helper for CSV and ZIP downloads.
        guild_id: Discord guild identifier.
        days: Rolling window size in days.

    Returns:
        None.
    """

    metrics = st.columns(4)
    metrics[0].metric("Total Messages", kpis.get("total_messages", 0))
    metrics[1].metric("Active Users", kpis.get("unique_authors", 0))
    metrics[2].metric("Busiest Channel", kpis.get("busiest_channel", "-"))
    metrics[3].metric("Avg / Day", f"{kpis.get('avg_messages_per_day', 0):.1f}")

    st.plotly_chart(line_activity_trend(activity_df), use_container_width=True)

    summary_record = dict(kpis)
    busiest_day = summary_record.get("busiest_day")
    if isinstance(busiest_day, datetime):
        summary_record["busiest_day"] = busiest_day.isoformat()

    report_files = {
        "overview_summary.csv": pd.DataFrame.from_records([summary_record]),
        "top_users.csv": top_users_df,
        "channel_breakdown.csv": channel_breakdown_df,
        "member_events.csv": member_events_df,
    }
    archive_filename = export_manager.generate_filename("full_report", guild_id, days).replace(".csv", ".zip")
    export_manager.get_zip_export_button(report_files, "Export Full Report", archive_filename)