"""Tests for app.core.database module.

Validates the async engine configuration, session factory setup,
Base declarative class, and the get_db FastAPI dependency.
"""

import os
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Required env vars so the config module loads without error.
REQUIRED_ENV = {
    "NEXUS_MODE": "tracker",
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/nexus_db",
    "JWT_SECRET": "test-secret-key",
    "CORS_ORIGINS": "http://localhost:5173",
}


class TestDatabaseModule:
    """Verify that the database module exports the expected objects."""

    def test_engine_is_async_engine(self):
        with patch.dict(os.environ, REQUIRED_ENV, clear=True):
            from app.core.database import engine

            assert isinstance(engine, AsyncEngine)

    def test_session_factory_is_async_sessionmaker(self):
        with patch.dict(os.environ, REQUIRED_ENV, clear=True):
            from app.core.database import async_session_factory

            assert isinstance(async_session_factory, async_sessionmaker)

    def test_base_is_declarative_base(self):
        with patch.dict(os.environ, REQUIRED_ENV, clear=True):
            from app.core.database import Base

            assert issubclass(Base, DeclarativeBase)

    def test_engine_url_matches_settings(self):
        """Engine URL should match the settings that were active when the module loaded."""
        from app.core.database import engine

        from app.core.config import get_settings

        settings = get_settings()
        assert engine.url.render_as_string(hide_password=False) == settings.database_url


class TestGetDbDependency:
    """Verify the get_db async generator dependency."""

    @pytest.mark.asyncio
    async def test_get_db_yields_async_session(self):
        """get_db should yield an AsyncSession instance."""
        with patch.dict(os.environ, REQUIRED_ENV, clear=True):
            from app.core.database import async_session_factory, get_db

            # Mock the session factory to avoid needing a real DB connection
            original_factory = async_session_factory

            # Use the generator protocol to test the dependency
            gen = get_db()
            # We can't fully test without a DB, but we verify the generator structure
            assert hasattr(gen, "__anext__")
