"""Repository layer for async database access and analytics queries."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncContextManager, Callable

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .engine import get_async_session
from .models import Channel, Guild, MemberEvent, Message

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncContextManager[AsyncSession]]


class Repository:
	"""Async repository for persistence and analytics queries."""

	def __init__(self, session_factory: SessionFactory = get_async_session) -> None:
		"""Initialize the repository with a session factory."""

		self._session_factory = session_factory

	async def upsert_guild(self, guild_id: str, name: str) -> Guild:
		"""Insert or update a guild row and return the persisted entity."""

		async with self._session_factory() as session:
			try:
				result = await session.execute(select(Guild).where(Guild.guild_id == guild_id))
				guild = result.scalar_one_or_none()

				if guild is None:
					guild = Guild(guild_id=guild_id, name=name)
					session.add(guild)
				else:
					guild.name = name

				await session.commit()
				await session.refresh(guild)
				return guild
			except IntegrityError:
				await session.rollback()
				logger.exception("Duplicate guild upsert failed for guild_id=%s", guild_id)

				result = await session.execute(select(Guild).where(Guild.guild_id == guild_id))
				guild = result.scalar_one()
				guild.name = name
				await session.commit()
				await session.refresh(guild)
				return guild
			except SQLAlchemyError:
				await session.rollback()
				logger.exception("Failed to upsert guild_id=%s", guild_id)
				raise

	async def upsert_channel(self, channel_id: str, guild_id: str, name: str, channel_type: str) -> Channel:
		"""Insert or update a channel row and return the persisted entity."""

		async with self._session_factory() as session:
			try:
				result = await session.execute(select(Channel).where(Channel.channel_id == channel_id))
				channel = result.scalar_one_or_none()

				if channel is None:
					channel = Channel(
						channel_id=channel_id,
						guild_id=guild_id,
						name=name,
						channel_type=channel_type,
					)
					session.add(channel)
				else:
					channel.guild_id = guild_id
					channel.name = name
					channel.channel_type = channel_type

				await session.commit()
				await session.refresh(channel)
				return channel
			except IntegrityError:
				await session.rollback()
				logger.exception("Duplicate channel upsert failed for channel_id=%s", channel_id)

				result = await session.execute(select(Channel).where(Channel.channel_id == channel_id))
				channel = result.scalar_one()
				channel.guild_id = guild_id
				channel.name = name
				channel.channel_type = channel_type
				await session.commit()
				await session.refresh(channel)
				return channel
			except SQLAlchemyError:
				await session.rollback()
				logger.exception("Failed to upsert channel_id=%s", channel_id)
				raise

	async def insert_message(
		self,
		message_id: str,
		guild_id: str,
		channel_id: str,
		author_id: str,
		author_name: str,
		content_length: int,
		has_attachments: bool,
		has_embeds: bool,
		timestamp: datetime,
	) -> Message | None:
		"""Insert a message or return ``None`` when a duplicate is encountered."""

		async with self._session_factory() as session:
			try:
				result = await session.execute(select(Message).where(Message.message_id == message_id))
				existing_message = result.scalar_one_or_none()
				if existing_message is not None:
					return None

				message = Message(
					message_id=message_id,
					guild_id=guild_id,
					channel_id=channel_id,
					author_id=author_id,
					author_name=author_name,
					content_length=content_length,
					has_attachments=has_attachments,
					has_embeds=has_embeds,
					timestamp=timestamp,
				)
				session.add(message)
				await session.commit()
				await session.refresh(message)
				return message
			except IntegrityError:
				await session.rollback()
				logger.info("Skipping duplicate message insertion for message_id=%s", message_id)
				return None
			except SQLAlchemyError:
				await session.rollback()
				logger.exception("Failed to insert message_id=%s", message_id)
				raise

	async def insert_member_event(
		self,
		guild_id: str,
		member_id: str,
		member_name: str,
		event_type: str,
		timestamp: datetime,
	) -> MemberEvent:
		"""Insert a member event and return the persisted entity."""

		async with self._session_factory() as session:
			try:
				event = MemberEvent(
					guild_id=guild_id,
					member_id=member_id,
					member_name=member_name,
					event_type=event_type,
					timestamp=timestamp,
				)
				session.add(event)
				await session.commit()
				await session.refresh(event)
				return event
			except IntegrityError:
				await session.rollback()
				logger.exception(
					"Duplicate member event insert failed for guild_id=%s member_id=%s event_type=%s",
					guild_id,
					member_id,
					event_type,
				)
				raise
			except SQLAlchemyError:
				await session.rollback()
				logger.exception(
					"Failed to insert member event for guild_id=%s member_id=%s event_type=%s",
					guild_id,
					member_id,
					event_type,
				)
				raise

	async def get_message_count_by_channel(self, guild_id: str, days: int = 30) -> list[dict[str, Any]]:
		"""Return message counts grouped by channel for the given guild."""

		cutoff = datetime.now(timezone.utc) - timedelta(days=days)

		async with self._session_factory() as session:
			try:
				query = (
					select(
						Message.channel_id.label("channel_id"),
						Channel.name.label("channel_name"),
						func.count(Message.id).label("message_count"),
					)
					.join(Channel, Channel.channel_id == Message.channel_id)
					.where(Message.guild_id == guild_id, Message.timestamp >= cutoff)
					.group_by(Message.channel_id, Channel.name)
					.order_by(func.count(Message.id).desc())
				)
				result = await session.execute(query)
				return [dict(row._mapping) for row in result.all()]
			except SQLAlchemyError:
				logger.exception("Failed to fetch message count by channel for guild_id=%s", guild_id)
				raise

	async def get_top_authors(
		self,
		guild_id: str,
		limit: int = 10,
		days: int = 30,
	) -> list[dict[str, Any]]:
		"""Return the top authors for the given guild and time window."""

		cutoff = datetime.now(timezone.utc) - timedelta(days=days)

		async with self._session_factory() as session:
			try:
				query = (
					select(
						Message.author_id.label("author_id"),
						Message.author_name.label("author_name"),
						func.count(Message.id).label("message_count"),
					)
					.where(Message.guild_id == guild_id, Message.timestamp >= cutoff)
					.group_by(Message.author_id, Message.author_name)
					.order_by(func.count(Message.id).desc())
					.limit(limit)
				)
				result = await session.execute(query)
				return [dict(row._mapping) for row in result.all()]
			except SQLAlchemyError:
				logger.exception("Failed to fetch top authors for guild_id=%s", guild_id)
				raise

	async def get_message_trend(self, guild_id: str, days: int = 30) -> list[dict[str, Any]]:
		"""Return daily message counts for the given guild."""

		cutoff = datetime.now(timezone.utc) - timedelta(days=days)

		async with self._session_factory() as session:
			try:
				query = (
					select(
						func.date(Message.timestamp).label("date"),
						func.count(Message.id).label("message_count"),
					)
					.where(Message.guild_id == guild_id, Message.timestamp >= cutoff)
					.group_by(func.date(Message.timestamp))
					.order_by(func.date(Message.timestamp))
				)
				result = await session.execute(query)
				return [dict(row._mapping) for row in result.all()]
			except SQLAlchemyError:
				logger.exception("Failed to fetch message trend for guild_id=%s", guild_id)
				raise

	async def get_member_events(self, guild_id: str, days: int = 30) -> list[dict[str, Any]]:
		"""Return daily member event counts grouped by event type."""

		cutoff = datetime.now(timezone.utc) - timedelta(days=days)

		async with self._session_factory() as session:
			try:
				query = (
					select(
						func.date(MemberEvent.timestamp).label("date"),
						MemberEvent.event_type.label("event_type"),
						func.count(MemberEvent.id).label("event_count"),
					)
					.where(MemberEvent.guild_id == guild_id, MemberEvent.timestamp >= cutoff)
					.group_by(func.date(MemberEvent.timestamp), MemberEvent.event_type)
					.order_by(func.date(MemberEvent.timestamp), MemberEvent.event_type)
				)
				result = await session.execute(query)
				return [dict(row._mapping) for row in result.all()]
			except SQLAlchemyError:
				logger.exception("Failed to fetch member events for guild_id=%s", guild_id)
				raise

	async def get_total_message_count(self, guild_id: str) -> int:
		"""Return the total number of tracked messages for a guild."""

		async with self._session_factory() as session:
			try:
				query = select(func.count(Message.id)).where(Message.guild_id == guild_id)
				result = await session.execute(query)
				return int(result.scalar_one() or 0)
			except SQLAlchemyError:
				logger.exception("Failed to fetch total message count for guild_id=%s", guild_id)
				raise

	async def get_total_member_event_count(self, guild_id: str) -> int:
		"""Return the total number of tracked member events for a guild."""

		async with self._session_factory() as session:
			try:
				query = select(func.count(MemberEvent.id)).where(MemberEvent.guild_id == guild_id)
				result = await session.execute(query)
				return int(result.scalar_one() or 0)
			except SQLAlchemyError:
				logger.exception("Failed to fetch total member event count for guild_id=%s", guild_id)
				raise