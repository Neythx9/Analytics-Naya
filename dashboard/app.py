"""Streamlit dashboard application for discord-analytics."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from analytics import ChannelAnalytics, MemberAnalytics, MessageAnalytics
from db import Repository
from dashboard.components import ExportManager
from dashboard.pages.channels import render as render_channels
from dashboard.pages.overview import render as render_overview
from dashboard.pages.trends import render as render_trends
from dashboard.pages.users import render as render_users
from utils import get_settings
from utils import setup_logging

logger = logging.getLogger(__name__)


def read_recent_logs(filepath: str, n: int = 100) -> list[str]:
    """Read the last ``n`` lines from a log file.

    Args:
        filepath: Path to the log file.
        n: Number of lines to return from the end of the file.

    Returns:
        A list containing the last ``n`` log lines.

    Raises:
        FileNotFoundError: If the file does not exist.
    """

    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(filepath)

    with path.open("r", encoding="utf-8") as log_file:
        lines = deque(log_file, maxlen=n)
    return [line.rstrip("\n") for line in lines]


def _resolve_guild_id(raw_guild_id: str) -> str:
    """Normalize the selected guild identifier.

    Args:
        raw_guild_id: Guild identifier from the sidebar.

    Returns:
        A normalized guild identifier string.
    """

    return raw_guild_id.strip()


async def _load_overview_data(
    message_analytics: MessageAnalytics,
    member_analytics: MemberAnalytics,
    channel_analytics: ChannelAnalytics,
    repository: Repository,
    guild_id: str,
    days: int,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load overview data frames for the dashboard.

    Args:
        message_analytics: Message analytics service.
        member_analytics: Member analytics service.
        channel_analytics: Channel analytics service.
        repository: Repository for raw member event data.
        guild_id: Discord guild identifier.
        days: Rolling window size in days.

    Returns:
        Summary stats and the supporting DataFrames.
    """

    summary = await message_analytics.get_summary_stats(guild_id=guild_id, days=days)
    activity_df = await message_analytics.get_activity_trend(guild_id=guild_id, days=min(days, 7))
    top_users_df = await message_analytics.get_top_authors(guild_id=guild_id, days=days)
    channel_breakdown_df = await channel_analytics.get_channel_breakdown(guild_id=guild_id, days=days)
    member_events_records = await repository.get_member_events(guild_id=guild_id, days=days)
    member_events_df = pd.DataFrame.from_records(member_events_records)
    return summary, activity_df, top_users_df, channel_breakdown_df, member_events_df


async def _load_users_data(message_analytics: MessageAnalytics, guild_id: str, days: int) -> pd.DataFrame:
    """Load top author data for the users page."""

    return await message_analytics.get_top_authors(guild_id=guild_id, days=days)


async def _load_channels_data(channel_analytics: ChannelAnalytics, guild_id: str, days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load channel data for the channels page."""

    breakdown_df = await channel_analytics.get_channel_breakdown(guild_id=guild_id, days=days)
    share_df = await channel_analytics.get_channel_share(guild_id=guild_id, days=days)
    return breakdown_df, share_df


async def _load_trends_data(
    message_analytics: MessageAnalytics,
    member_analytics: MemberAnalytics,
    guild_id: str,
    days: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load trend data for the trends page."""

    activity_df = await message_analytics.get_activity_trend(guild_id=guild_id, days=days)
    growth_df = await member_analytics.get_growth_trend(guild_id=guild_id, days=days)
    heatmap_df = await message_analytics.get_hourly_heatmap(guild_id=guild_id, days=days)
    return activity_df, growth_df, heatmap_df


def main() -> None:
    """Launch the Streamlit dashboard."""

    settings = get_settings(require_token=False)
    setup_logging(settings)

    st.set_page_config(page_title="Discord Analytics", page_icon="📊", layout="wide")

    repository = Repository()
    export_manager = ExportManager(settings.EXPORT_DIR)
    message_analytics = MessageAnalytics(repository)
    member_analytics = MemberAnalytics(repository)
    channel_analytics = ChannelAnalytics(repository)

    st.sidebar.title("Discord Analytics")
    pages = ["Overview", "Users", "Channels", "Trends"]
    selected_page = st.sidebar.selectbox("Page", pages)
    days = st.sidebar.slider("Days", min_value=7, max_value=90, value=30)

    if settings.DISCORD_GUILD_IDS:
        selected_guild = st.sidebar.selectbox(
            "Guild",
            [str(guild_id) for guild_id in settings.DISCORD_GUILD_IDS],
        )
    else:
        selected_guild = st.sidebar.text_input("Guild ID", value="")

    with st.sidebar.expander("📋 Recent Logs", expanded=False):
        if st.button("Refresh Logs", key="refresh_logs"):
            st.rerun()

        try:
            recent_logs = read_recent_logs(settings.LOG_FILE, n=100)
            st.code("\n".join(recent_logs), language=None)
        except FileNotFoundError:
            st.info("No log file found")
        except Exception:
            logger.exception("Failed to load recent logs from %s", settings.LOG_FILE)
            st.error("Failed to load recent logs.")

    guild_id = _resolve_guild_id(selected_guild)
    if not guild_id:
        st.warning("Select a guild ID to load dashboard data.")
        return

    try:
        if selected_page == "Overview":
            summary, activity_df, top_users_df, channel_breakdown_df, member_events_df = asyncio.run(
                _load_overview_data(
                    message_analytics=message_analytics,
                    member_analytics=member_analytics,
                    channel_analytics=channel_analytics,
                    repository=repository,
                    guild_id=guild_id,
                    days=days,
                )
            )
            render_overview(
                summary,
                activity_df,
                top_users_df,
                channel_breakdown_df,
                member_events_df,
                export_manager,
                guild_id,
                days,
            )
        elif selected_page == "Users":
            users_df = asyncio.run(_load_users_data(message_analytics, guild_id, days))
            render_users(users_df, export_manager, guild_id, days)
        elif selected_page == "Channels":
            breakdown_df, share_df = asyncio.run(_load_channels_data(channel_analytics, guild_id, days))
            render_channels(breakdown_df, share_df, export_manager, guild_id, days)
        else:
            activity_df, growth_df, heatmap_df = asyncio.run(
                _load_trends_data(message_analytics, member_analytics, guild_id, days)
            )
            render_trends(activity_df, growth_df, heatmap_df, export_manager, guild_id, days)
    except Exception:
        logger.exception("Failed to render dashboard page %s for guild_id=%s", selected_page, guild_id)
        st.error("Failed to load dashboard data.")


if __name__ == "__main__":
    main()