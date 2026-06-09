"""
Application configuration loaded from environment variables.

Overview:
    Defines typed runtime settings for the FX Pulse API using Pydantic Settings.
    Values may be overridden via environment variables or a local ``.env`` file.

Constants:
    REPO_ROOT: Absolute path to the repository root directory.

Classes:
    Settings: Typed configuration model for all service settings.

Functions:
    get_settings: Return a cached ``Settings`` instance for the process.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT: Path = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """
    Runtime settings for the FX Pulse API service.

    Attributes:
        app_env: Deployment environment label (for example ``development``).
        app_version: Semantic version string exposed by health endpoints.
        log_level: Python logging level name.
        cors_origins: Comma-separated list of allowed CORS origins.
        frankfurter_base: Base URL for the Frankfurter public FX API.
        default_from: Default base currency code.
        default_to: Default quote currency code.
        cache_ttl_seconds: TTL for Redis FX response cache entries.
        max_retries: Maximum retry attempts for Frankfurter HTTP requests.
        retry_backoff_seconds: Initial backoff delay between retries.
        circuit_breaker_threshold: Failures required before opening the circuit.
        circuit_breaker_cooldown_seconds: Seconds the circuit remains open.
        rate_limit_per_minute: Allowed ``/summary`` requests per IP per minute.
        redis_url: Redis connection URL for shared cache, limits, and breaker state.
        sample_fx_path: Filesystem path to offline fallback JSON data.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8000"

    frankfurter_base: str = "https://api.frankfurter.dev"
    default_from: str = "EUR"
    default_to: str = "USD"
    cache_ttl_seconds: int = 300
    max_retries: int = 3
    retry_backoff_seconds: float = 0.5
    circuit_breaker_threshold: int = 5
    circuit_breaker_cooldown_seconds: int = 30
    rate_limit_per_minute: int = 60
    redis_url: str = "redis://localhost:6379/0"
    sample_fx_path: Path = REPO_ROOT / "data" / "sample_fx.json"

    @property
    def cors_origin_list(self) -> list[str]:
        """
        Parse ``cors_origins`` into a list of origin strings.

        Returns:
            List of trimmed, non-empty CORS origin URLs.
        """
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached settings instance for the process lifetime.

    Returns:
        Singleton ``Settings`` object loaded from environment and defaults.
    """
    return Settings()
