"""Application configuration loaded from environment variables.

Uses Pydantic v2 BaseSettings for validation and type safety.
Required variables cause a fast startup failure if missing.
"""

from enum import Enum
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NexusMode(str, Enum):
    """Platform operating mode."""

    TRACKER = "tracker"
    PORTFOLIO = "portfolio"


class StorageBackendType(str, Enum):
    """Storage backend selection."""

    LOCAL = "local"
    CLOUD = "cloud"


class LLMProviderType(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required fields (NEXUS_MODE, DATABASE_URL, JWT_SECRET, CORS_ORIGINS)
    will cause a validation error at startup if not set, ensuring
    fast failure on misconfiguration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Required ---
    nexus_mode: NexusMode
    database_url: str
    jwt_secret: str
    cors_origins: str

    # --- Optional with defaults ---
    jwt_expiry_minutes: int = 60
    storage_backend: StorageBackendType = StorageBackendType.LOCAL
    storage_local_path: str = "./uploads"

    # --- Optional LLM configuration ---
    llm_provider: Optional[LLMProviderType] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    anthropic_model: Optional[str] = None

    # --- Optional cloud storage configuration ---
    cloud_storage_bucket: Optional[str] = None
    cloud_storage_region: Optional[str] = None
    cloud_storage_endpoint: Optional[str] = None
    cloud_storage_access_key: Optional[str] = None
    cloud_storage_secret_key: Optional[str] = None

    # --- Optional webhook configuration ---
    webhook_url: Optional[str] = None
    webhook_auth_header: Optional[str] = None

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """Ensure CORS origins is a non-empty string."""
        if not v or not v.strip():
            raise ValueError("CORS_ORIGINS must not be empty")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_tracker_mode(self) -> bool:
        """Check if the platform is running in Tracker Mode."""
        return self.nexus_mode == NexusMode.TRACKER

    @property
    def is_portfolio_mode(self) -> bool:
        """Check if the platform is running in Portfolio Mode."""
        return self.nexus_mode == NexusMode.PORTFOLIO


def get_settings() -> Settings:
    """Create and return a validated Settings instance.

    Raises ValidationError at startup if required environment
    variables are missing or have invalid values.
    """
    return Settings()
