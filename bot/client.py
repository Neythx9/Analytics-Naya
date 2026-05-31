"""Discord bot client for the discord-analytics project."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands

import db
from db import Repository
from utils import Settings

logger = logging.getLogger(__name__)


class AnalyticsBot(commands.Bot):
    """Discord bot that captures guild, channel, and message analytics."""

    __version__ = "0.1.0"

    def __init__(self, settings: Settings, repository: Repository) -> None:
        """Initialize the bot with application settings and a repository."""

        self.settings = settings
        self.repository = repository
        self.start_time = datetime.now(timezone.utc)

        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        intents.messages = True

        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        """Initialize the database and load bot extensions."""

        await db.init_db()
        if self.get_command("health") is None:
            self.add_command(self.health)
        await self.load_extension("bot.events.messages")
        await self.load_extension("bot.events.members")
        logger.info(
            "Bot startup prepared: username=%s guild_count=%s",
            self.user,
            len(self.guilds),
        )

    async def on_ready(self) -> None:
        """Handle the bot becoming ready and synchronize guild metadata."""

        if self.user is None:
            logger.warning("Bot is ready but user object is unavailable.")
            return

        logger.info("Bot ready: username=%s id=%s", self.user, self.user.id)

        for guild in self.guilds:
            await self.repository.upsert_guild(str(guild.id), guild.name)

            for channel in guild.text_channels:
                await self.repository.upsert_channel(
                    channel_id=str(channel.id),
                    guild_id=str(guild.id),
                    name=channel.name,
                    channel_type=channel.type.name,
                )

    async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Log uncaught event errors with a full traceback."""

        logger.exception("Unhandled error in event %s", event)

    async def close(self) -> None:
        """Shut down the bot cleanly with a shutdown log entry."""

        logger.info("Shutting down bot client.")
        await super().close()

    @commands.command(name="health")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def health(self, ctx: commands.Context[commands.Bot]) -> None:
        """Report the current bot health to guild administrators."""

        try:
            uptime_delta = datetime.now(timezone.utc) - self.start_time
            guild_id = str(ctx.guild.id) if ctx.guild is not None else ""
            total_messages = await self.repository.get_total_message_count(guild_id) if guild_id else 0
            total_member_events = await self.repository.get_total_member_event_count(guild_id) if guild_id else 0

            database_path = self._resolve_database_path()
            database_size_mb = database_path.stat().st_size / (1024 * 1024) if database_path.exists() else 0.0

            embed = discord.Embed(
                title="Bot Health",
                color=discord.Color.green(),
            )
            embed.add_field(name="Uptime", value=str(uptime_delta).split(".", maxsplit=1)[0], inline=True)
            embed.add_field(name="Total Messages Tracked", value=str(total_messages), inline=True)
            embed.add_field(name="Total Member Events Tracked", value=str(total_member_events), inline=True)
            embed.add_field(name="Database Size (MB)", value=f"{database_size_mb:.2f}", inline=True)
            embed.add_field(name="Current Log Level", value=self.settings.LOG_LEVEL, inline=True)
            embed.set_footer(text=f"discord-analytics v{self.__version__}")

            await ctx.reply(embed=embed, mention_author=False)
        except Exception:
            logger.exception("Failed to generate health report for guild_id=%s", getattr(ctx.guild, "id", None))
            await ctx.reply("Unable to generate health report right now.", mention_author=False)

    def _resolve_database_path(self) -> Path:
        """Resolve the SQLite database path from the configured database URL."""

        database_url = self.settings.DATABASE_URL
        if database_url.startswith("sqlite+aiosqlite:///"):
            return Path(database_url.replace("sqlite+aiosqlite:///", "", 1))
        if database_url.startswith("sqlite:///"):
            return Path(database_url.replace("sqlite:///", "", 1))
        return Path("discord_analytics.db")