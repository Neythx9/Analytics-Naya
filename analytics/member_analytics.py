"""Member analytics services built on top of repository data and pandas."""

from __future__ import annotations

import logging
from datetime import timezone
from typing import Any

import pandas as pd

from db import Repository

logger = logging.getLogger(__name__)


class MemberAnalytics:
    """Generate member growth and retention analytics for a Discord guild."""

    def __init__(self, repository: Repository) -> None:
        """Store the repository used to access persisted analytics data."""

        self.repository = repository

    def _empty_frame(self, columns: list[str]) -> pd.DataFrame:
        """Create an empty DataFrame with the requested columns."""

        return pd.DataFrame.from_records([], columns=columns)

    def _date_window(self, days: int) -> tuple[pd.Timestamp, pd.DatetimeIndex]:
        """Return the inclusive start date and daily date index for a window."""

        end_date = pd.Timestamp.now(tz=timezone.utc).normalize()
        start_date = end_date - pd.Timedelta(days=max(days, 1) - 1)
        return start_date, pd.date_range(start=start_date, end=end_date, freq="D")

    async def get_growth_trend(self, guild_id: str, days: int = 30) -> pd.DataFrame:
        """Return daily joins, leaves, and cumulative net member growth."""

        columns = ["date", "joins", "leaves", "net_change", "cumulative_net"]

        try:
            records = await self.repository.get_member_events(guild_id=guild_id, days=days)
            _, date_index = self._date_window(days)

            if not records:
                frame = pd.DataFrame({"date": date_index, "joins": 0, "leaves": 0})
            else:
                frame = pd.DataFrame.from_records(records)
                frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
                frame["event_count"] = pd.to_numeric(frame["event_count"], errors="coerce").fillna(0).astype(int)
                frame = frame.dropna(subset=["date"])
                frame = frame.pivot_table(
                    index="date",
                    columns="event_type",
                    values="event_count",
                    aggfunc="sum",
                    fill_value=0,
                ).reset_index()

                for column in ("join", "leave"):
                    if column not in frame.columns:
                        frame[column] = 0

                frame = frame.rename(columns={"join": "joins", "leave": "leaves"})

                frame = pd.DataFrame({"date": date_index}).merge(frame, on="date", how="left")
                frame[["joins", "leaves"]] = frame[["joins", "leaves"]].fillna(0)

            frame["joins"] = pd.to_numeric(frame["joins"], errors="coerce").fillna(0).astype(int)
            frame["leaves"] = pd.to_numeric(frame["leaves"], errors="coerce").fillna(0).astype(int)
            frame["net_change"] = frame["joins"] - frame["leaves"]
            frame["cumulative_net"] = frame["net_change"].cumsum()
            frame = frame.sort_values("date").reset_index(drop=True)
            return frame[columns]
        except Exception:
            logger.exception("Failed to build growth trend for guild_id=%s", guild_id)
            return self._empty_frame(columns)

    async def get_retention_summary(self, guild_id: str, days: int = 30) -> dict[str, Any]:
        """Return a summary of member retention and churn over a period."""

        try:
            trend = await self.get_growth_trend(guild_id=guild_id, days=days)
            total_joins = int(trend["joins"].sum()) if not trend.empty else 0
            total_leaves = int(trend["leaves"].sum()) if not trend.empty else 0
            net_growth = total_joins - total_leaves
            churn_rate = (total_leaves / total_joins * 100.0) if total_joins else 0.0

            return {
                "total_joins": total_joins,
                "total_leaves": total_leaves,
                "net_growth": net_growth,
                "churn_rate": float(churn_rate),
            }
        except Exception:
            logger.exception("Failed to build retention summary for guild_id=%s", guild_id)
            return {
                "total_joins": 0,
                "total_leaves": 0,
                "net_growth": 0,
                "churn_rate": 0.0,
            }