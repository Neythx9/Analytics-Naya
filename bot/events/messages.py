"""Message event listeners for the analytics bot."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from bot.client import AnalyticsBot

logger = logging.getLogger(__name__)


class MessageEvents(commands.Cog):
    """Capture message activity for analytics storage."""

    def __init__(self, bot: AnalyticsBot) -> None:
        """Store a reference to the running bot instance."""

        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Persist a message record when a non-bot user posts in a guild."""

        if message.guild is None or message.author.bot:
            return

        try:
            await self.bot.repository.insert_message(
                message_id=str(message.id),
                guild_id=str(message.guild.id),
                channel_id=str(message.channel.id),
                author_id=str(message.author.id),
                author_name=message.author.display_name,
                content_length=len(message.content),
                has_attachments=bool(message.attachments),
                has_embeds=bool(message.embeds),
                timestamp=message.created_at,
            )
        except Exception:
            logger.exception("Failed to persist message_id=%s", message.id)


async def setup(bot: commands.Bot) -> None:
    """Register the message event cog."""

    await bot.add_cog(MessageEvents(bot))