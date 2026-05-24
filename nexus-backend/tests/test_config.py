"""Tests for app.core.config module.

Validates that the Settings class correctly loads environment variables,
fails fast on missing required values, and parses optional fields.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import (
    LLMProviderType,
    NexusMode,
    Settings,
    StorageBackendType,
)

# Minimal required env vars for a valid Settings instance
REQUIRED_ENV = {
    "NEXUS_MODE": "tracker",
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/nexus_db",
    "JWT_SECRET": "test-secret-key",
    "CORS_ORIGINS": "http://localhost:5173",
}


class TestSettingsRequiredFields:
    """Settings must fail fast when required env vars are missing."""

    def test_missing_nexus_mode_raises(self):
        env = {k: v for k, v in REQUIRED_ENV.items() if k != "NEXUS_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_missing_database_url_raises(self):
        env = {k: v for k, v in REQUIRED_ENV.items() if k != "DATABASE_URL"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_missing_jwt_secret_raises(self):
        env = {k: v for k, v in REQUIRED_ENV.items() if k != "JWT_SECRET"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_missing_cors_origins_raises(self):
        env = {k: v for k, v in REQUIRED_ENV.items() if k != "CORS_ORIGINS"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_invalid_nexus_mode_raises(self):
        env = {**REQUIRED_ENV, "NEXUS_MODE": "invalid"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError):
                Settings()


class TestSettingsValidConfig:
    """Settings loads correctly with valid environment variables."""

    def test_loads_required_fields(self):
        with patch.dict(os.environ, REQUIRED_ENV, clear=True):
            settings = Settings()
            assert settings.nexus_mode == NexusMode.TRACKER
            assert settings.database_url == REQUIRED_ENV["DATABASE_URL"]
            assert settings.jwt_secret == REQUIRED_ENV["JWT_SECRET"]
            assert settings.cors_origins == REQUIRED_ENV["CORS_ORIGINS"]

    def test_default_optional_values(self):
        with patch.dict(os.environ, REQUIRED_ENV, clear=True):
            settings = Settings()
            assert settings.jwt_expiry_minutes == 60
            assert settings.storage_backend == StorageBackendType.LOCAL
            assert settings.storage_local_path == "./uploads"
            assert settings.llm_provider is None
            assert settings.openai_api_key is None
            assert settings.openai_model is None
            assert settings.anthropic_api_key is None
            assert settings.anthropic_model is None
            assert settings.webhook_url is None
            assert settings.webhook_auth_header is None

    def test_portfolio_mode(self):
        env = {**REQUIRED_ENV, "NEXUS_MODE": "portfolio"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.nexus_mode == NexusMode.PORTFOLIO
            assert settings.is_portfolio_mode is True
            assert settings.is_tracker_mode is False

    def test_tracker_mode_properties(self):
        with patch.dict(os.environ, REQUIRED_ENV, clear=True):
            settings = Settings()
            assert settings.is_tracker_mode is True
            assert settings.is_portfolio_mode is False

    def test_cors_origins_list_parsing(self):
        env = {**REQUIRED_ENV, "CORS_ORIGINS": "http://localhost:5173, http://localhost:3000"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.cors_origins_list == [
                "http://localhost:5173",
                "http://localhost:3000",
            ]

    def test_optional_llm_config(self):
        env = {
            **REQUIRED_ENV,
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_MODEL": "gpt-4o",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.llm_provider == LLMProviderType.OPENAI
            assert settings.openai_api_key == "sk-test"
            assert settings.openai_model == "gpt-4o"

    def test_optional_webhook_config(self):
        env = {
            **REQUIRED_ENV,
            "WEBHOOK_URL": "https://example.com/webhook",
            "WEBHOOK_AUTH_HEADER": "Bearer token123",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.webhook_url == "https://example.com/webhook"
            assert settings.webhook_auth_header == "Bearer token123"

    def test_custom_jwt_expiry(self):
        env = {**REQUIRED_ENV, "JWT_EXPIRY_MINUTES": "120"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.jwt_expiry_minutes == 120

    def test_cloud_storage_backend(self):
        env = {**REQUIRED_ENV, "STORAGE_BACKEND": "cloud"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.storage_backend == StorageBackendType.CLOUD
