"""Async SQLAlchemy engine and session helpers for discord-analytics."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from utils import get_settings

from .models import Base

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def create_async_engine_from_settings() -> AsyncEngine:
    """Create a cached async engine using the configured database URL."""

    settings = get_settings()
    engine_kwargs = {"echo": False, "pool_pre_ping": True}

    if settings.DATABASE_URL.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    return create_async_engine(settings.DATABASE_URL, **engine_kwargs)


@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session bound to the configured engine."""

    session_factory = async_sessionmaker(
        bind=create_async_engine_from_settings(),
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session


async def init_db() -> None:
    """Create all database tables defined by the ORM metadata."""

    engine = create_async_engine_from_settings()

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    except SQLAlchemyError:
        logger.exception("Failed to initialize the database schema.")
        raise
