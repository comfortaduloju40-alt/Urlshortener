"""
Application configuration.

Loads and validates all environment variables in one place using
pydantic-settings. Every other module imports `settings` from here
instead of calling os.getenv() directly — this keeps config validation
centralized and fails fast on startup if something required is missing.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Telegram ---
    BOT_TOKEN: str
    WEBHOOK_URL: str
    WEBHOOK_SECRET: str

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./shortener.db"

    # --- Short link settings ---
    SHORT_DOMAIN: str
    SHORT_CODE_LENGTH: int = 6

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    # --- Environment ---
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def webhook_path(self) -> str:
        """Path Telegram will POST updates to. Includes the secret so the
        endpoint isn't guessable from just knowing the domain."""
        return f"/webhook/{self.WEBHOOK_SECRET}"

    @property
    def full_webhook_url(self) -> str:
        return f"{self.WEBHOOK_URL.rstrip('/')}{self.webhook_path}"


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance. Using lru_cache means the .env file is
    parsed once per process, not on every import.
    """
    return Settings()


settings = get_settings()
