"""
Application configuration via pydantic-settings.

All settings are loaded from environment variables (and .env file via python-dotenv).
This is the SINGLE source of truth for configuration — no os.getenv() scattered elsewhere.

Usage:
    from app.core.config import settings
    print(settings.gemini_api_key)
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from .env file and environment variables.

    Environment variables override .env values. All keys are case-insensitive.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Don't crash on unrecognized env vars
    )

    # --- LLM: Gemini (Primary) ---
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model name",
    )

    # --- LLM: Groq (Fallback) ---
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model name for fallback",
    )

    # --- LLM Behavior ---
    llm_max_retries: int = Field(default=2, description="Max retries per provider before fallback")
    llm_retry_base_wait: float = Field(default=1.0, description="Base wait (seconds) for retry backoff")
    llm_retry_max_wait: float = Field(default=8.0, description="Max wait (seconds) for retry backoff")
    llm_default_temperature: float = Field(default=0.7, description="Default LLM temperature")
    llm_default_max_tokens: int = Field(default=1024, description="Default max output tokens")

    # --- Supabase ---
    supabase_url: str = Field(default="", description="Supabase project URL")
    supabase_key: str = Field(default="", description="Supabase service role or anon key")

    # --- Application ---
    app_env: str = Field(default="development", description="Environment: development | production")
    app_host: str = Field(default="0.0.0.0", description="Server bind host")
    app_port: int = Field(default=8000, description="Server bind port")
    log_level: str = Field(default="INFO", description="Logging level")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton. Call this instead of constructing Settings() directly."""
    return Settings()


# Module-level convenience — importable as `from app.core.config import settings`
settings = get_settings()
