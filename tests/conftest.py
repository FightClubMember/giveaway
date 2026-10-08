"""Pytest configuration and async database fixtures."""

import pytest
import pytest_asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from aiogram import Bot

from database.models import Base, utcnow, Giveaway, GiveawayStatus


@pytest_asyncio.fixture
async def test_session():
    """Create an isolated in-memory SQLite database session for each test."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session

    await test_engine.dispose()


@pytest.fixture
def mock_bot():
    """Mock aiogram Bot instance for verification and messaging."""
    bot = AsyncMock(spec=Bot)
    bot.get_chat_member = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


@pytest_asyncio.fixture
async def sample_giveaway(test_session: AsyncSession) -> Giveaway:
    """Create a sample active giveaway fixture."""
    gw = Giveaway(
        title="Test iPhone 16 Giveaway",
        description="Win a brand new iPhone 16 Pro",
        prize="iPhone 16 Pro 256GB",
        winners_count=2,
        status=GiveawayStatus.ACTIVE.value,
        start_time=utcnow(),
        end_time=utcnow() + timedelta(days=2),
        referral_bonus=2,
        max_entries_per_user=20,
        rules="Standard rules",
        auto_draw=True,
    )
    test_session.add(gw)
    await test_session.commit()
    return gw
