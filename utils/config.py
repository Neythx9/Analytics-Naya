"""Application configuration and environment variable loading utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

DEFAULT_DATABASE_URL: Final[str] = "sqlite+aiosqlite:///./discord_analytics.db"
DEFAULT_LOG_LEVEL: Final[str] = "INFO"
DEFAULT_LOG_FILE: Final[str] = "logs/bot.log"
DEFAULT_DASHBOARD_PORT: Final[int] = 8501
DEFAULT_EXPORT_DIR: Final[str] = "exports"


@dataclass(frozen=True, slots=True)
class Settings:
    """Typed application settings loaded from environment variables."""

    DISCORD_TOKEN: str
    DISCORD_GUILD_IDS: list[int]
    DATABASE_URL: str = DEFAULT_DATABASE_URL
    LOG_LEVEL: str = DEFAULT_LOG_LEVEL
    LOG_FILE: str = DEFAULT_LOG_FILE
    DASHBOARD_PORT: int = DEFAULT_DASHBOARD_PORT
    EXPORT_DIR: str = DEFAULT_EXPORT_DIR


def _parse_guild_ids(raw_value: str) -> list[int]:
    """Parse a comma-separated list of guild IDs into integers."""

    guild_ids: list[int] = []

    for item in raw_value.split(","):
        value = item.strip()
        if not value:
            continue

        try:
            guild_ids.append(int(value))
        except ValueError as exc:
            raise ValueError(
                f"Invalid DISCORD_GUILD_IDS value {value!r}; expected a comma-separated list of integers."
            ) from exc

    return guild_ids


def _parse_dashboard_port(raw_value: str) -> int:
    """Convert the dashboard port to an integer with validation."""

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid DASHBOARD_PORT value {raw_value!r}; expected an integer."
        ) from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load environment variables and return a cached settings object."""

    # Load project-level environment values before reading from os.environ.
    load_dotenv(dotenv_path=Path(".env"), override=False)

    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "DISCORD_TOKEN is required and was not found in the environment or .env file."
        )

    guild_ids_raw = os.getenv("DISCORD_GUILD_IDS", "")
    guild_ids = _parse_guild_ids(guild_ids_raw)

    return Settings(
        DISCORD_TOKEN=token,
        DISCORD_GUILD_IDS=guild_ids,
        DATABASE_URL=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip()
        or DEFAULT_DATABASE_URL,
        LOG_LEVEL=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).strip() or DEFAULT_LOG_LEVEL,
        LOG_FILE=os.getenv("LOG_FILE", DEFAULT_LOG_FILE).strip() or DEFAULT_LOG_FILE,
        DASHBOARD_PORT=_parse_dashboard_port(
            os.getenv("DASHBOARD_PORT", str(DEFAULT_DASHBOARD_PORT)).strip()
            or str(DEFAULT_DASHBOARD_PORT)
        ),
        EXPORT_DIR=os.getenv("EXPORT_DIR", DEFAULT_EXPORT_DIR).strip() or DEFAULT_EXPORT_DIR,
    )