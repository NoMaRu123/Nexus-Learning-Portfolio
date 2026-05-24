"""Tests for app.api.auth module.

Validates registration and login endpoints using mocked database sessions.
"""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.security import AuthService

# Minimal required env vars for a valid Settings instance
REQUIRED_ENV = {
    "NEXUS_MODE": "tracker",
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/nexus_db",
    "JWT_SECRET": "test-secret-key-for-unit-tests",
    "CORS_ORIGINS": "http://localhost:5173",
}


def _make_settings(**overrides: str) -> Settings:
    """Create a Settings instance with test defaults and optional overrides."""
    env = {**REQUIRED_ENV, **overrides}
    with patch.dict(os.environ, env, clear=True):
        return Settings()


def _make_auth_service() -> AuthService:
    """Create an AuthService with test settings."""
    return AuthService(_make_settings())


class TestRegisterEndpoint:
    """POST /api/auth/register endpoint tests."""

    @pytest.mark.asyncio
    async def test_register_success_creates_user_and_profile(self):
        """Successful registration creates UserAccount + UserProfile."""
        from app.api.auth import register
        from app.schemas.auth import RegisterRequest

        request = RegisterRequest(email="new@example.com", password="securepass123")
        auth_service = _make_auth_service()

        # Mock DB: no existing user found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()  # add() is synchronous in SQLAlchemy

        response = await register(request=request, db=mock_db, auth_service=auth_service)

        assert response.message == "User registered successfully"
        assert response.user_id  # non-empty UUID string
        # Verify db.add was called twice (UserAccount + UserProfile)
        assert mock_db.add.call_count == 2
        # Verify flush was called to get the user ID before creating profile
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_409(self):
        """Registration with existing email returns 409 Conflict."""
        from fastapi import HTTPException

        from app.api.auth import register
        from app.schemas.auth import RegisterRequest

        request = RegisterRequest(email="existing@example.com", password="securepass123")
        auth_service = _make_auth_service()

        # Mock DB: existing user found
        existing_user = MagicMock()
        existing_user.email = "existing@example.com"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await register(request=request, db=mock_db, auth_service=auth_service)

        assert exc_info.value.status_code == 409
        assert "existing@example.com" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_register_hashes_password(self):
        """Registration stores a bcrypt-hashed password, not plaintext."""
        from app.api.auth import register
        from app.schemas.auth import RegisterRequest

        request = RegisterRequest(email="hash@example.com", password="securepass123")
        auth_service = _make_auth_service()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()

        await register(request=request, db=mock_db, auth_service=auth_service)

        # The first db.add call should be the UserAccount
        user_account = mock_db.add.call_args_list[0][0][0]
        assert user_account.hashed_password != "securepass123"
        assert user_account.hashed_password.startswith("$2b$")

    @pytest.mark.asyncio
    async def test_register_creates_default_empty_profile(self):
        """Registration creates a UserProfile linked to the new UserAccount."""
        from app.api.auth import register
        from app.models.profile import UserProfile
        from app.schemas.auth import RegisterRequest

        request = RegisterRequest(email="profile@example.com", password="securepass123")
        auth_service = _make_auth_service()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()

        await register(request=request, db=mock_db, auth_service=auth_service)

        # The second db.add call should be the UserProfile
        profile = mock_db.add.call_args_list[1][0][0]
        assert isinstance(profile, UserProfile)
        # Profile fields should be empty/None by default
        assert profile.name is None
        assert profile.bio is None


class TestLoginEndpoint:
    """POST /api/auth/login endpoint tests."""

    @pytest.mark.asyncio
    async def test_login_success_returns_token(self):
        """Successful login returns a JWT access token."""
        from app.api.auth import login
        from app.schemas.auth import LoginRequest

        auth_service = _make_auth_service()
        password = "correct-password"
        hashed = auth_service.hash_password(password)

        # Mock user in DB
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "user@example.com"
        mock_user.hashed_password = hashed

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        request = LoginRequest(email="user@example.com", password=password)
        response = await login(request=request, db=mock_db, auth_service=auth_service)

        assert response.access_token
        assert response.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self):
        """Login with wrong password returns 401 with generic message."""
        from fastapi import HTTPException

        from app.api.auth import login
        from app.schemas.auth import LoginRequest

        auth_service = _make_auth_service()
        hashed = auth_service.hash_password("correct-password")

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.hashed_password = hashed

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        request = LoginRequest(email="user@example.com", password="wrong-password")

        with pytest.raises(HTTPException) as exc_info:
            await login(request=request, db=mock_db, auth_service=auth_service)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid credentials"

    @pytest.mark.asyncio
    async def test_login_nonexistent_email_returns_401(self):
        """Login with non-existent email returns 401 with generic message."""
        from fastapi import HTTPException

        from app.api.auth import login
        from app.schemas.auth import LoginRequest

        auth_service = _make_auth_service()

        # No user found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        request = LoginRequest(email="nobody@example.com", password="any-password")

        with pytest.raises(HTTPException) as exc_info:
            await login(request=request, db=mock_db, auth_service=auth_service)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid credentials"

    @pytest.mark.asyncio
    async def test_login_error_does_not_reveal_which_field_was_wrong(self):
        """Login failure message is identical for wrong email and wrong password."""
        from fastapi import HTTPException

        from app.api.auth import login
        from app.schemas.auth import LoginRequest

        auth_service = _make_auth_service()
        hashed = auth_service.hash_password("correct-password")

        # Case 1: wrong email (user not found)
        mock_result_no_user = MagicMock()
        mock_result_no_user.scalar_one_or_none.return_value = None
        mock_db_no_user = AsyncMock()
        mock_db_no_user.execute.return_value = mock_result_no_user

        with pytest.raises(HTTPException) as exc_wrong_email:
            await login(
                request=LoginRequest(email="wrong@example.com", password="any"),
                db=mock_db_no_user,
                auth_service=auth_service,
            )

        # Case 2: wrong password (user found)
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.hashed_password = hashed
        mock_result_user = MagicMock()
        mock_result_user.scalar_one_or_none.return_value = mock_user
        mock_db_user = AsyncMock()
        mock_db_user.execute.return_value = mock_result_user

        with pytest.raises(HTTPException) as exc_wrong_pass:
            await login(
                request=LoginRequest(email="user@example.com", password="wrong"),
                db=mock_db_user,
                auth_service=auth_service,
            )

        # Both errors should have identical status and message
        assert exc_wrong_email.value.status_code == exc_wrong_pass.value.status_code
        assert exc_wrong_email.value.detail == exc_wrong_pass.value.detail

    @pytest.mark.asyncio
    async def test_login_returns_valid_jwt(self):
        """Login returns a JWT that can be decoded with the correct secret."""
        from jose import jwt as jose_jwt

        from app.api.auth import login
        from app.schemas.auth import LoginRequest

        auth_service = _make_auth_service()
        user_id = uuid.uuid4()
        password = "correct-password"
        hashed = auth_service.hash_password(password)

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.hashed_password = hashed

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        request = LoginRequest(email="user@example.com", password=password)
        response = await login(request=request, db=mock_db, auth_service=auth_service)

        # Decode the token and verify it contains the user ID
        payload = jose_jwt.decode(
            response.access_token,
            REQUIRED_ENV["JWT_SECRET"],
            algorithms=["HS256"],
        )
        assert payload["sub"] == str(user_id)


class TestAuthSchemas:
    """Pydantic schema validation tests."""

    def test_register_request_rejects_short_password(self):
        """RegisterRequest requires password of at least 8 characters."""
        from pydantic import ValidationError

        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="short")

    def test_register_request_rejects_invalid_email(self):
        """RegisterRequest requires a valid email format."""
        from pydantic import ValidationError

        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(email="not-an-email", password="securepass123")

    def test_register_request_accepts_valid_input(self):
        """RegisterRequest accepts valid email and password."""
        from app.schemas.auth import RegisterRequest

        req = RegisterRequest(email="valid@example.com", password="securepass123")
        assert req.email == "valid@example.com"
        assert req.password == "securepass123"

    def test_login_request_accepts_any_password_length(self):
        """LoginRequest does not enforce minimum password length."""
        from app.schemas.auth import LoginRequest

        req = LoginRequest(email="user@example.com", password="short")
        assert req.password == "short"

    def test_token_response_defaults_to_bearer(self):
        """TokenResponse defaults token_type to 'bearer'."""
        from app.schemas.auth import TokenResponse

        resp = TokenResponse(access_token="some-token")
        assert resp.token_type == "bearer"
