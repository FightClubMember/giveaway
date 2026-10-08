"""Database engine and session management.
Supports async SQLite (for development & tests) and async PostgreSQL (for production).
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from config import settings
from database.models import Base

logger = logging.getLogger(__name__)

# Normalize sqlite URL if needed (ensure sqlite+aiosqlite)
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://")
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database schemas and create tables if they do not exist."""
    async with engine.begin() as conn:
        logger.info("Initializing database schema...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an asynchronous transactional database session scope."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Dispose of engine connections cleanly."""
    await engine.dispose()
    logger.info("Database connections closed.")
