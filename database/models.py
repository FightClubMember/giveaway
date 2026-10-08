"""SQLAlchemy database models for Telegram Giveaway Platform.
Supports SQLite and PostgreSQL.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    """Current UTC datetime."""
    return datetime.now(timezone.utc)


class GiveawayStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    CANCELLED = "cancelled"


class EntryType(str, Enum):
    BASE = "base"
    REFERRAL = "referral"
    DAILY = "daily"
    CUSTOM = "custom"


class ClaimStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INFO_REQUESTED = "info_requested"


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)  # Telegram User ID
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    referrer_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    is_banned = Column(Boolean, default=False, nullable=False, index=True)
    ban_reason = Column(Text, nullable=True)
    last_daily_bonus_at = Column(DateTime(timezone=True), nullable=True)
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    referrals_made = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer")
    referral_received = relationship("Referral", foreign_keys="Referral.referred_id", back_populates="referred", uselist=False)
    participants = relationship("Participant", back_populates="user", cascade="all, delete-orphan")
    entries = relationship("Entry", back_populates="user", cascade="all, delete-orphan")
    wins = relationship("Winner", back_populates="user")

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join([p for p in parts if p]) or f"User #{self.id}"

    @property
    def mention(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.full_name


class Giveaway(Base):
    __tablename__ = "giveaways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    prize = Column(String(255), nullable=False)
    winners_count = Column(Integer, default=1, nullable=False)
    status = Column(String(32), default=GiveawayStatus.ACTIVE.value, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    referral_bonus = Column(Integer, default=1, nullable=False)
    max_entries_per_user = Column(Integer, default=100, nullable=False)
    image_url = Column(String(1024), nullable=True)
    rules = Column(Text, nullable=True)
    auto_draw = Column(Boolean, default=True, nullable=False)
    created_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    requirements = relationship("GiveawayRequirement", back_populates="giveaway", cascade="all, delete-orphan")
    participants = relationship("Participant", back_populates="giveaway", cascade="all, delete-orphan")
    entries = relationship("Entry", back_populates="giveaway", cascade="all, delete-orphan")
    winners = relationship("Winner", back_populates="giveaway", cascade="all, delete-orphan")


class GiveawayRequirement(Base):
    __tablename__ = "giveaway_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    giveaway_id = Column(Integer, ForeignKey("giveaways.id", ondelete="CASCADE"), nullable=True, index=True)
    chat_id = Column(String(255), nullable=False)  # @username or -100xxxxxxxxxx
    title = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    invite_link = Column(String(512), nullable=True)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    giveaway = relationship("Giveaway", back_populates="requirements")


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    giveaway_id = Column(Integer, ForeignKey("giveaways.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_verified = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    giveaway = relationship("Giveaway", back_populates="participants")
    user = relationship("User", back_populates="participants")

    __table_args__ = (
        UniqueConstraint("giveaway_id", "user_id", name="uq_giveaway_user"),
    )


class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    giveaway_id = Column(Integer, ForeignKey("giveaways.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_type = Column(String(32), default=EntryType.BASE.value, nullable=False)
    amount = Column(Integer, default=1, nullable=False)
    reference_id = Column(String(255), nullable=True)  # e.g., referred user ID or task ID
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    giveaway = relationship("Giveaway", back_populates="entries")
    user = relationship("User", back_populates="entries")

    __table_args__ = (
        Index("ix_entries_giveaway_user", "giveaway_id", "user_id"),
    )


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    referred_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    is_valid = Column(Boolean, default=False, nullable=False, index=True)  # True once referred joins a giveaway
    rewarded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_made")
    referred = relationship("User", foreign_keys=[referred_id], back_populates="referral_received")


class Winner(Base):
    __tablename__ = "winners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    giveaway_id = Column(Integer, ForeignKey("giveaways.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rank = Column(Integer, default=1, nullable=False)
    entries_count = Column(Integer, default=1, nullable=False)
    selection_hash = Column(String(128), nullable=True)  # Auditable proof hash
    selected_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    giveaway = relationship("Giveaway", back_populates="winners")
    user = relationship("User", back_populates="wins")
    claim = relationship("WinnerClaim", back_populates="winner", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("giveaway_id", "user_id", name="uq_winner_giveaway_user"),
    )


class WinnerClaim(Base):
    __tablename__ = "winner_claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    winner_id = Column(Integer, ForeignKey("winners.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    giveaway_id = Column(Integer, ForeignKey("giveaways.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_data = Column(Text, nullable=False)  # Sensitive address/payment details entered privately
    status = Column(String(32), default=ClaimStatus.PENDING.value, nullable=False, index=True)
    admin_notes = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    claimed_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(BigInteger, nullable=True)

    winner = relationship("Winner", back_populates="claim")


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(BigInteger, nullable=False)
    message_text = Column(Text, nullable=False)
    total_targets = Column(Integer, default=0, nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AdminLog(Base):
    __tablename__ = "admin_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(64), nullable=False)
    details = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    giveaway_id = Column(Integer, ForeignKey("giveaways.id", ondelete="CASCADE"), nullable=True)
    entries_amount = Column(Integer, default=5, nullable=False)
    max_uses = Column(Integer, default=100, nullable=False)
    uses_count = Column(Integer, default=0, nullable=False)
    created_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    giveaway = relationship("Giveaway")


class PromoCodeRedemption(Base):
    __tablename__ = "promo_code_redemptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code_id = Column(Integer, ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    redeemed_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("code_id", "user_id", name="uq_code_user_redemption"),
    )
