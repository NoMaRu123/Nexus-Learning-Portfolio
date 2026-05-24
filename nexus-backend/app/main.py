"""FastAPI application entry point.

Creates the FastAPI app instance, configures CORS, rate limiting,
and mode-aware middleware, and includes all API routers.
"""

import logging

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.auth import router as auth_router
from app.api.bot import limiter
from app.api.bot import router as bot_router
from app.api.entries import router as entries_router
from app.api.profile import router as profile_router
from app.api.projects import router as projects_router
from app.api.search import router as search_router
from app.api.skills import router as skills_router
from app.core.config import NexusMode, get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Nexus Learning & Portfolio API",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# Rate limiting (slowapi) — must be configured before routes are added
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS middleware — origins loaded from CORS_ORIGINS env var
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mode-aware middleware
# ---------------------------------------------------------------------------
# Paths exempt from Portfolio Mode write restrictions (auth, bot, docs).
_EXEMPT_PATHS: set[str] = {
    "/api/auth/register",
    "/api/auth/login",
    "/api/bot/chat",
    "/docs",
    "/openapi.json",
}

# HTTP methods considered write operations.
_WRITE_METHODS: set[str] = {"POST", "PUT", "DELETE", "PATCH"}


@app.middleware("http")
async def mode_aware_middleware(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    """Enforce Portfolio Mode access restrictions.

    In Portfolio Mode:
      - GET (read) requests are allowed through without authentication.
      - POST / PUT / DELETE requests from unauthenticated visitors are
        rejected with 403.
    In Tracker Mode:
      - All requests pass through; authentication is handled by
        individual endpoint dependencies.

    Exempt paths (auth, bot, docs) are always allowed regardless of
    mode or method.
    """
    if settings.nexus_mode == NexusMode.PORTFOLIO:
        path = request.url.path.rstrip("/")

        if path not in _EXEMPT_PATHS and request.method in _WRITE_METHODS:
            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Write operations require authentication in Portfolio Mode"},
                )

    return await call_next(request)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(skills_router)
app.include_router(projects_router)
app.include_router(entries_router)
app.include_router(search_router)
app.include_router(profile_router)
app.include_router(bot_router)
