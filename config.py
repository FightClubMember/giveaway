"""Configuration settings for Telegram Giveaway Bot.
Supports environment variables from .env file or container environment.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Bot Credentials
    BOT_TOKEN: str = Field(default="YOUR_BOT_TOKEN_HERE", description="Telegram Bot API Token from @BotFather")
    BOT_USERNAME: str = Field(default="GiveawayHubBot", description="Bot username without @")

    # Admin IDs (comma-separated or list of integers)
    ADMIN_IDS: str = Field(default="123456789", description="Comma-separated Telegram user IDs of administrators")

    # Database
    # Default is SQLite for easy local dev; set to postgresql+asyncpg://user:pass@host:5432/dbname for production
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///giveaway_bot.db",
        description="SQLAlchemy async connection URL"
    )

    # Branding
    BOT_NAME: str = Field(default="John's Giveaway Bot", description="Display name of the platform")

    # Groq AI Settings
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq Cloud API Key for ultra-fast AI intelligence")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile", description="Groq model ID")

    # Operational Settings
    DEFAULT_REFERRAL_BONUS: int = Field(default=1, description="Default extra entries per valid referral")
    DAILY_BONUS_ENTRIES: int = Field(default=1, description="Daily bonus entry value")
    CLAIM_WINDOW_HOURS: int = Field(default=24, description="Hours a winner has to claim their prize")
    RATE_LIMIT_DELAY: float = Field(default=0.04, description="Delay between broadcast messages in seconds (approx 25 msgs/sec)")
    SUPPORT_URL: str = Field(default="https://t.me/support_contact", description="Support contact or Telegram link")
    COMMUNITY_CHANNEL: Optional[str] = Field(default="@GiveawayHubChannel", description="Default official community channel")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")

    @property
    def admin_id_list(self) -> List[int]:
        """Parse comma-separated ADMIN_IDS into a list of integers."""
        if not self.ADMIN_IDS:
            return []
        ids = []
        for raw_id in str(self.ADMIN_IDS).split(","):
            cleaned = raw_id.strip()
            if cleaned.isdigit() or (cleaned.startswith("-") and cleaned[1:].isdigit()):
                ids.append(int(cleaned))
        return ids

    def is_admin(self, user_id: int) -> bool:
        """Check if a Telegram user ID is recognized as an administrator."""
        return user_id in self.admin_id_list


settings = Settings()
