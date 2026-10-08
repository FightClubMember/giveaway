import asyncio
import logging
import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from config import settings
from database.models import Base

logger = logging.getLogger(__name__)

def get_normalized_db_url(raw_url: str) -> str:
    """Normalize database connection URL for async SQLAlchemy compatibility and IPv4 pooler routing."""
    url = raw_url.strip()
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Supabase IPv6 fix for Render/Docker environments:
    # Direct hostname 'db.<project_ref>.supabase.co:5432' is IPv6-only.
    # Convert automatically to Supabase's IPv4 connection pooler to prevent [Errno 101] Network is unreachable.
    supabase_match = re.search(r'@db\.([a-z0-9]+)\.supabase\.co:5432', url)
    if supabase_match:
        ref = supabase_match.group(1)
        # Update user to user.<ref> if not already formatted
        if f"://postgres:" in url:
            url = url.replace("://postgres:", f"://postgres.{ref}:", 1)
        # Point to IPv4-compatible pooler
        pooler_host = "aws-0-ap-southeast-1.pooler.supabase.com:5432"
        url = url.replace(f"db.{ref}.supabase.co:5432", pooler_host)
        logger.info("Automatically routed Supabase direct connection to IPv4 pooler host: %s", pooler_host)

    return url

db_url = get_normalized_db_url(settings.DATABASE_URL)

# Configure engine kwargs
engine_kwargs = {
    "echo": False,
    "future": True,
}

if not db_url.startswith("sqlite"):
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_async_engine(db_url, **engine_kwargs)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def init_db(max_retries: int = 5, retry_delay: int = 3) -> None:
    """Initialize database schemas with retry logic for cloud container deployments."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Initializing database schema (Attempt %d/%d)...", attempt, max_retries)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema initialized successfully.")
            return
        except Exception as e:
            logger.warning("Database connection failed (Attempt %d/%d): %s", attempt, max_retries, e)
            if attempt == max_retries:
                logger.error("Max database retries reached. Failing initialization.")
                raise
            await asyncio.sleep(retry_delay)

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

