"""Root conftest.py — sets required environment variables before test collection.

This file is loaded by pytest before any test modules are collected,
ensuring that the Settings class can validate successfully when modules
like app.core.database are imported at collection time.
"""

import os

# Set required environment variables for testing BEFORE any app modules are imported.
# These provide valid defaults so that Pydantic Settings validation passes during
# module-level initialization (e.g., database.py calling get_settings() at import time).
os.environ.setdefault("NEXUS_MODE", "tracker")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/nexus_test_db"
)
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
