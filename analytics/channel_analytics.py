"""Channel analytics services built on top of repository data and pandas."""

from __future__ import annotations

import logging
from datetime import timezone
from typing import Any

import pandas as pd
from sqlalchemy import func, select

from db import Channel, Message, Repository

logger = logging.getLogger(__name__)


class ChannelAnalytics:
    """Generate channel-focused analytics for a Discord guild."""

    def __init__(self, repository: Repository) -> None:
        """Store the repository used to access persisted analytics data."""

        self.repository = repository

    def _empty_frame(self, columns: list[str]) -> pd.DataFrame:
        """Create an empty DataFrame with the requested columns."""

        return pd.DataFrame.from_records([], columns=columns)

    def _session_factory(self):
        """Return the repository session factory used for ad hoc queries."""

        return getattr(self.repository, "_session_factory")

    def _date_window(self, days: int) -> pd.Timestamp:
        """Return the inclusive start date for a rolling window."""

        return pd.Timestamp.now(tz=timezone.utc).normalize() - pd.Timedelta(days=max(days, 1) - 1)

    async def get_channel_breakdown(self, guild_id: str, days: int = 30) -> pd.DataFrame:
        """Return per-channel message activity and content statistics."""

        columns = ["channel_name", "channel_id", "message_count", "unique_authors", "avg_content_length"]

        try:
            start_date = self._date_window(days)
            async with self._session_factory()() as session:
                query = (
                    select(
                        Channel.name.label("channel_name"),
                        Message.channel_id.label("channel_id"),
                        func.count(Message.id).label("message_count"),
                        func.count(func.distinct(Message.author_id)).label("unique_authors"),
                        func.avg(Message.content_length).label("avg_content_length"),
                    )
                    .join(Channel, Channel.channel_id == Message.channel_id)
                    .where(Message.guild_id == guild_id, Message.timestamp >= start_date.to_pydatetime())
                    .group_by(Channel.name, Message.channel_id)
                    .order_by(func.count(Message.id).desc())
                )
                result = await session.execute(query)
                records = [dict(row._mapping) for row in result.all()]

            if not records:
                return self._empty_frame(columns)

            frame = pd.DataFrame.from_records(records)
            frame["message_count"] = pd.to_numeric(frame["message_count"], errors="coerce").fillna(0).astype(int)
            frame["unique_authors"] = pd.to_numeric(frame["unique_authors"], errors="coerce").fillna(0).astype(int)
            frame["avg_content_length"] = pd.to_numeric(frame["avg_content_length"], errors="coerce").fillna(0.0)
            frame = frame[["channel_name", "channel_id", "message_count", "unique_authors", "avg_content_length"]]
            frame = frame.sort_values("message_count", ascending=False).reset_index(drop=True)
            return frame
        except Exception:
            logger.exception("Failed to build channel breakdown for guild_id=%s", guild_id)
            return self._empty_frame(columns)

    async def get_channel_share(self, guild_id: str, days: int = 30) -> pd.DataFrame:
        """Return each channel's share of total messages as a percentage."""

        columns = ["channel_name", "message_count", "share_pct"]

        try:
            breakdown = await self.get_channel_breakdown(guild_id=guild_id, days=days)
            if breakdown.empty:
                return self._empty_frame(columns)

            total_messages = float(breakdown["message_count"].sum())
            frame = breakdown[["channel_name", "message_count"]].copy()
            frame["share_pct"] = (frame["message_count"] / total_messages * 100.0) if total_messages else 0.0
            frame = frame.sort_values("message_count", ascending=False).reset_index(drop=True)
            return frame[columns]
        except Exception:
            logger.exception("Failed to build channel share for guild_id=%s", guild_id)
            return self._empty_frame(columns)