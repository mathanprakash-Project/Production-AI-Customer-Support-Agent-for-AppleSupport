"""
Database session and connection management.
Supports async PostgreSQL with pgvector, and automatic fallback to SQLite for standalone runs.
"""

import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

logger = logging.getLogger(__name__)


def _make_engine_and_factory(url: str):
    connect_args = {}
    if "sqlite" in url:
        connect_args["check_same_thread"] = False
    eng = create_async_engine(
        url,
        echo=settings.DEBUG,
        future=True,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
    factory = async_sessionmaker(
        bind=eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return eng, factory


# Primary database engine
engine, async_session_factory = _make_engine_and_factory(settings.DATABASE_URL)
_fallback_active = False


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session with automatic SQLite fallback."""
    global engine, async_session_factory, _fallback_active

    if not _fallback_active and "postgresql" in settings.DATABASE_URL:
        # Check connectivity
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            logger.warning(
                f"PostgreSQL connection failed ({e}). "
                f"Falling back to local SQLite database (sqlite+aiosqlite:///./tweetsupport.db)."
            )
            engine, async_session_factory = _make_engine_and_factory("sqlite+aiosqlite:///./tweetsupport.db")
            _fallback_active = True
            # Initialize SQLite schema
            from app.db.init_db import init_db
            await init_db(engine, async_session_factory)

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_standalone_session() -> AsyncSession:
    """Convenience helper for standalone CLI scripts with automatic SQLite fallback."""
    global engine, async_session_factory, _fallback_active

    if not _fallback_active and "postgresql" in settings.DATABASE_URL:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            logger.warning(
                f"PostgreSQL connection failed ({e}). "
                f"Falling back to local SQLite database (sqlite+aiosqlite:///./tweetsupport.db)."
            )
            engine, async_session_factory = _make_engine_and_factory("sqlite+aiosqlite:///./tweetsupport.db")
            _fallback_active = True
            from app.db.init_db import init_db
            await init_db(engine, async_session_factory)

    return async_session_factory()
