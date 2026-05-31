"""Entry point for the Discord bot application."""

from __future__ import annotations

import asyncio
import logging

from bot import AnalyticsBot
from db import Repository
from utils import get_settings, setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    """Load configuration, initialize the bot, and start the Discord client."""

    settings = get_settings()
    setup_logging(settings)

    repository = Repository()
    bot = AnalyticsBot(settings=settings, repository=repository)

    try:
        await bot.start(settings.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user.")
    except SystemExit:
        logger.info("Bot exited cleanly.")
    except Exception:
        logger.exception("Bot execution failed.")
        raise
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
