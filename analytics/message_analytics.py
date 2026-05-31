"""Message analytics services built on top of repository data and pandas."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
from sqlalchemy import distinct, func, select

from db import Channel, Message, Repository

logger = logging.getLogger(__name__)


class MessageAnalytics:
    """Generate message-focused analytics for a Discord guild."""

    def __init__(self, repository: Repository) -> None:
        """Store the repository used to access persisted analytics data."""

        self.repository = repository

    def _empty_frame(self, columns: list[str]) -> pd.DataFrame:
        """Create an empty DataFrame with the requested columns."""

        return pd.DataFrame.from_records([], columns=columns)

    def _session_factory(self) -> Callable[[], Any]:
        """Return the repository session factory used for ad hoc queries."""

        return getattr(self.repository, "_session_factory")

    def _date_window(self, days: int) -> tuple[pd.Timestamp, pd.DatetimeIndex]:
        """Return the inclusive start date and continuous daily index for a window."""

        end_date = pd.Timestamp.now(tz=timezone.utc).normalize()
        start_date = end_date - pd.Timedelta(days=max(days, 1) - 1)
        return start_date, pd.date_range(start=start_date, end=end_date, freq="D")

    async def get_top_authors(self, guild_id: str, limit: int = 10, days: int = 30) -> pd.DataFrame:
        """Return the top message authors for a guild as a DataFrame."""

        try:
            records = await self.repository.get_top_authors(guild_id=guild_id, limit=limit, days=days)
            if not records:
                return self._empty_frame(["author_name", "author_id", "message_count", "avg_content_length"])

            frame = pd.DataFrame.from_records(records)
            frame = frame.rename(columns={"author_id": "author_id"})

            start_date, _ = self._date_window(days)
            end_date = pd.Timestamp.now(tz=timezone.utc)

            async with self._session_factory()() as session:
                query = (
                    select(
                        Message.author_name.label("author_name"),
                        Message.author_id.label("author_id"),
                        func.count(Message.id).label("message_count"),
                        func.avg(Message.content_length).label("avg_content_length"),
                    )
                    .where(Message.guild_id == guild_id, Message.timestamp >= start_date.to_pydatetime())
                    .group_by(Message.author_name, Message.author_id)
                    .order_by(func.count(Message.id).desc())
                    .limit(limit)
                )
                result = await session.execute(query)
                frame = pd.DataFrame.from_records([dict(row._mapping) for row in result.all()])

            if frame.empty:
                return self._empty_frame(["author_name", "author_id", "message_count", "avg_content_length"])

            frame = frame[["author_name", "author_id", "message_count", "avg_content_length"]]
            frame["message_count"] = pd.to_numeric(frame["message_count"], errors="coerce").fillna(0).astype(int)
            frame["avg_content_length"] = pd.to_numeric(frame["avg_content_length"], errors="coerce").fillna(0.0)
            frame = frame.sort_values("message_count", ascending=False).reset_index(drop=True)
            return frame
        except Exception:
            logger.exception("Failed to build top authors analytics for guild_id=%s", guild_id)
            return self._empty_frame(["author_name", "author_id", "message_count", "avg_content_length"])

    async def get_activity_trend(self, guild_id: str, days: int = 30) -> pd.DataFrame:
        """Return the daily message activity trend for a guild."""

        columns = ["date", "message_count"]

        try:
            records = await self.repository.get_message_trend(guild_id=guild_id, days=days)
            start_date, date_index = self._date_window(days)

            if not records:
                return pd.DataFrame({"date": date_index, "message_count": [0] * len(date_index)})

            frame = pd.DataFrame.from_records(records)
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
            frame["message_count"] = pd.to_numeric(frame["message_count"], errors="coerce").fillna(0).astype(int)
            frame = frame.dropna(subset=["date"])
            frame = frame.groupby("date", as_index=False, observed=True)["message_count"].sum()

            frame = (
                pd.DataFrame({"date": date_index})
                .merge(frame, on="date", how="left")
                .fillna({"message_count": 0})
            )
            frame["message_count"] = frame["message_count"].astype(int)
            frame = frame.sort_values("date").reset_index(drop=True)
            return frame[columns]
        except Exception:
            logger.exception("Failed to build activity trend for guild_id=%s", guild_id)
            return self._empty_frame(columns)

    async def get_hourly_heatmap(self, guild_id: str, days: int = 30) -> pd.DataFrame:
        """Return hourly message density by day of week for heatmap rendering."""

        columns = ["hour", "day_of_week", "message_count"]

        try:
            start_date, _ = self._date_window(days)
            async with self._session_factory()() as session:
                query = (
                    select(
                        func.strftime("%H", Message.timestamp).label("hour"),
                        func.strftime("%w", Message.timestamp).label("weekday"),
                        func.count(Message.id).label("message_count"),
                    )
                    .where(Message.guild_id == guild_id, Message.timestamp >= start_date.to_pydatetime())
                    .group_by(func.strftime("%H", Message.timestamp), func.strftime("%w", Message.timestamp))
                )
                result = await session.execute(query)
                records = [dict(row._mapping) for row in result.all()]

            if not records:
                return pd.DataFrame(
                    [{"hour": hour, "day_of_week": day_of_week, "message_count": 0} for day_of_week in range(7) for hour in range(24)]
                )

            frame = pd.DataFrame.from_records(records)
            frame["hour"] = pd.to_numeric(frame["hour"], errors="coerce").fillna(0).astype(int)
            frame["day_of_week"] = pd.to_numeric(frame["weekday"], errors="coerce").fillna(0).astype(int)
            frame["day_of_week"] = frame["day_of_week"].replace({0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5})
            frame["message_count"] = pd.to_numeric(frame["message_count"], errors="coerce").fillna(0).astype(int)
            frame = frame[["hour", "day_of_week", "message_count"]]

            complete_index = pd.MultiIndex.from_product([range(24), range(7)], names=["hour", "day_of_week"])
            frame = (
                frame.groupby(["hour", "day_of_week"], as_index=False, observed=True)["message_count"].sum()
                .set_index(["hour", "day_of_week"])
                .reindex(complete_index, fill_value=0)
                .reset_index()
            )
            frame["message_count"] = frame["message_count"].astype(int)
            return frame[columns]
        except Exception:
            logger.exception("Failed to build hourly heatmap for guild_id=%s", guild_id)
            return self._empty_frame(columns)

    async def get_summary_stats(self, guild_id: str, days: int = 30) -> dict[str, Any]:
        """Return a summary of message activity for the requested guild."""

        try:
            trend = await self.get_activity_trend(guild_id=guild_id, days=days)
            channel_breakdown = await self.repository.get_message_count_by_channel(guild_id=guild_id, days=days)
            top_authors = await self.repository.get_top_authors(guild_id=guild_id, limit=1, days=days)

            start_date, _ = self._date_window(days)
            async with self._session_factory()() as session:
                query = select(func.count(Message.id), func.count(distinct(Message.author_id))).where(
                    Message.guild_id == guild_id,
                    Message.timestamp >= start_date.to_pydatetime(),
                )
                result = await session.execute(query)
                total_messages, unique_authors = result.one()

            busiest_channel = None
            if channel_breakdown:
                busiest_channel = channel_breakdown[0].get("channel_name")

            busiest_day = None
            if not trend.empty:
                busiest_row = trend.sort_values("message_count", ascending=False).iloc[0]
                busiest_day = pd.Timestamp(busiest_row["date"]).to_pydatetime()

            avg_messages_per_day = float(total_messages or 0) / float(max(days, 1))

            return {
                "total_messages": int(total_messages or 0),
                "unique_authors": int(unique_authors or 0),
                "busiest_channel": busiest_channel,
                "busiest_day": busiest_day,
                "avg_messages_per_day": avg_messages_per_day,
            }
        except Exception:
            logger.exception("Failed to build summary stats for guild_id=%s", guild_id)
            return {
                "total_messages": 0,
                "unique_authors": 0,
                "busiest_channel": None,
                "busiest_day": None,
                "avg_messages_per_day": 0.0,
            }