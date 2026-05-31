"""Member and guild event listeners for the analytics bot."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from bot.client import AnalyticsBot

logger = logging.getLogger(__name__)


class MembersCog(commands.Cog):
    """Capture guild member lifecycle events for analytics storage."""

    def __init__(self, bot: AnalyticsBot) -> None:
        """Store a reference to the running bot instance."""

        self.bot = bot

    def _should_track_guild(self, guild_id: int) -> bool:
        """Return ``True`` when the guild is configured for tracking."""

        return guild_id in self.bot.settings.DISCORD_GUILD_IDS

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Persist a member join event for configured guilds."""

        if not self._should_track_guild(member.guild.id):
            return

        try:
            await self.bot.repository.insert_member_event(
                guild_id=str(member.guild.id),
                member_id=str(member.id),
                member_name=member.display_name,
                event_type="join",
                timestamp=discord.utils.utcnow(),
            )
            logger.info("%s joined %s", member.display_name, member.guild.name)
        except Exception:
            logger.exception("Failed to persist member join event for member_id=%s", member.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Persist a member leave event for configured guilds."""

        if not self._should_track_guild(member.guild.id):
            return

        try:
            await self.bot.repository.insert_member_event(
                guild_id=str(member.guild.id),
                member_id=str(member.id),
                member_name=member.display_name,
                event_type="leave",
                timestamp=discord.utils.utcnow(),
            )
            logger.info("%s left %s", member.display_name, member.guild.name)
        except Exception:
            logger.exception("Failed to persist member leave event for member_id=%s", member.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Persist newly joined guild metadata."""

        try:
            await self.bot.repository.upsert_guild(str(guild.id), guild.name)
            logger.info("Joined guild %s (%s)", guild.name, guild.id)
        except Exception:
            logger.exception("Failed to persist guild join event for guild_id=%s", guild.id)


async def setup(bot: AnalyticsBot) -> None:
    """Register the member events cog."""

    await bot.add_cog(MembersCog(bot))