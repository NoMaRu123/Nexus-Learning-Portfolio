"""Tests for app.main module.

Validates FastAPI app wiring, CORS configuration, mode-aware middleware,
and router inclusion.
"""

import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


# Minimal required env vars for a valid Settings instance
REQUIRED_ENV = {
    "NEXUS_MODE": "tracker",
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/nexus_db",
    "JWT_SECRET": "test-secret-key-for-unit-tests",
    "CORS_ORIGINS": "http://localhost:5173",
}


def _create_app(nexus_mode: str = "tracker"):
    """Create a fresh FastAPI app with the given mode.

    Reloads the main module so that the module-level settings
    pick up the patched environment.
    """
    import importlib

    env = {**REQUIRED_ENV, "NEXUS_MODE": nexus_mode}
    with patch.dict(os.environ, env, clear=True):
        # Clear cached settings so get_settings() re-reads env
        import app.core.config as config_mod

        if hasattr(config_mod.get_settings, "cache_clear"):
            config_mod.get_settings.cache_clear()

        import app.main as main_mod

        importlib.reload(main_mod)
        return main_mod.app


class TestAppWiring:
    """Verify that all routers are included and docs are mounted."""

    def test_openapi_docs_url(self):
        """OpenAPI docs are available at /docs."""
        application = _create_app()
        assert application.docs_url == "/docs"

    def test_openapi_json_url(self):
        """OpenAPI JSON spec is available at /openapi.json."""
        application = _create_app()
        assert application.openapi_url == "/openapi.json"

    def test_app_title(self):
        """App title matches spec."""
        application = _create_app()
        assert application.title == "Nexus Learning & Portfolio API"

    def test_all_routers_included(self):
        """All expected route prefixes are registered."""
        application = _create_app()
        route_paths = {route.path for route in application.routes if hasattr(route, "path")}

        expected_prefixes = [
            "/api/auth/register",
            "/api/auth/login",
            "/api/skills",
            "/api/projects",
            "/api/entries",
            "/api/search",
            "/api/profile",
        ]
        for prefix in expected_prefixes:
            assert any(
                path.startswith(prefix) for path in route_paths
            ), f"Missing route prefix: {prefix}"


class TestCORSMiddleware:
    """Verify CORS middleware is configured from settings."""

    @pytest.mark.asyncio
    async def test_cors_allows_configured_origin(self):
        """CORS preflight from a configured origin returns allow headers."""
        application = _create_app()
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.options(
                "/api/skills",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    @pytest.mark.asyncio
    async def test_cors_rejects_unconfigured_origin(self):
        """CORS preflight from an unconfigured origin does not return allow headers."""
        application = _create_app()
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.options(
                "/api/skills",
                headers={
                    "Origin": "http://evil.example.com",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert "access-control-allow-origin" not in response.headers


class TestModeAwareMiddlewarePortfolio:
    """Verify Portfolio Mode middleware blocks unauthenticated writes."""

    @pytest.mark.asyncio
    async def test_portfolio_mode_blocks_post_without_auth(self):
        """POST to a non-exempt path without auth returns 403 in Portfolio Mode."""
        application = _create_app(nexus_mode="portfolio")
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/skills", json={"name": "Python", "category": "lang"})
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_portfolio_mode_blocks_put_without_auth(self):
        """PUT without auth returns 403 in Portfolio Mode."""
        application = _create_app(nexus_mode="portfolio")
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                "/api/skills/00000000-0000-0000-0000-000000000001",
                json={"name": "Updated"},
            )
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_portfolio_mode_blocks_delete_without_auth(self):
        """DELETE without auth returns 403 in Portfolio Mode."""
        application = _create_app(nexus_mode="portfolio")
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                "/api/skills/00000000-0000-0000-0000-000000000001",
            )
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_portfolio_mode_allows_exempt_auth_register(self):
        """POST to /api/auth/register is exempt from Portfolio Mode restrictions."""
        from unittest.mock import AsyncMock, MagicMock

        from app.core.database import get_db

        application = _create_app(nexus_mode="portfolio")

        # Override get_db to avoid real DB connection — we only test middleware behavior
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        async def _mock_db():
            db = AsyncMock()
            db.execute.return_value = mock_result
            db.add = MagicMock()
            yield db

        application.dependency_overrides[get_db] = _mock_db

        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/register",
                json={"email": "test@example.com", "password": "securepass123"},
            )
            # Should NOT be 403 — the middleware lets exempt paths through
            assert response.status_code != 403

        application.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_portfolio_mode_allows_exempt_auth_login(self):
        """POST to /api/auth/login is exempt from Portfolio Mode restrictions."""
        from unittest.mock import AsyncMock, MagicMock

        from app.core.database import get_db

        application = _create_app(nexus_mode="portfolio")

        # Override get_db to avoid real DB connection — we only test middleware behavior
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        async def _mock_db():
            db = AsyncMock()
            db.execute.return_value = mock_result
            yield db

        application.dependency_overrides[get_db] = _mock_db

        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "securepass123"},
            )
            # Should NOT be 403 — the middleware lets exempt paths through
            # It will be 401 (invalid credentials) since mock returns no user
            assert response.status_code != 403

        application.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_portfolio_mode_allows_write_with_bearer_token(self):
        """POST with a Bearer token passes the middleware (may fail at endpoint level)."""
        application = _create_app(nexus_mode="portfolio")
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/skills",
                json={"name": "Python", "category": "lang"},
                headers={"Authorization": "Bearer some-token"},
            )
            # Should NOT be 403 — the middleware lets it through.
            # It may be 401 (invalid token) or 500 (no DB), but not 403.
            assert response.status_code != 403

    @pytest.mark.asyncio
    async def test_portfolio_mode_returns_403_detail_message(self):
        """403 response includes a descriptive detail message."""
        application = _create_app(nexus_mode="portfolio")
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/skills", json={"name": "Python", "category": "lang"})
            assert response.status_code == 403
            body = response.json()
            assert "detail" in body
            assert "Portfolio Mode" in body["detail"]


class TestModeAwareMiddlewareTracker:
    """Verify Tracker Mode middleware passes all requests through."""

    @pytest.mark.asyncio
    async def test_tracker_mode_allows_post_without_auth(self):
        """POST without auth in Tracker Mode is not blocked by middleware.

        The request may fail at the endpoint level (401 from get_current_user),
        but the middleware itself should not return 403.
        """
        application = _create_app(nexus_mode="tracker")
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/skills", json={"name": "Python", "category": "lang"})
            # In Tracker Mode, middleware passes through — endpoint returns 401 (no token)
            assert response.status_code != 403

    @pytest.mark.asyncio
    async def test_tracker_mode_allows_delete_without_auth(self):
        """DELETE without auth in Tracker Mode is not blocked by middleware."""
        application = _create_app(nexus_mode="tracker")
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                "/api/skills/00000000-0000-0000-0000-000000000001",
            )
            assert response.status_code != 403
