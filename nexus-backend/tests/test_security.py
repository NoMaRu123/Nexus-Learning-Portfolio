"""Tests for app.core.security module.

Validates password hashing, JWT creation/decoding, and the
get_current_user FastAPI dependency.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt as jose_jwt

from app.core.config import Settings
from app.core.security import AuthService, TokenPayload, get_current_user

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


class TestPasswordHashing:
    """AuthService password hashing and verification."""

    def test_hash_password_returns_bcrypt_hash(self):
        settings = _make_settings()
        auth = AuthService(settings)
        hashed = auth.hash_password("my-secret-password")
        assert hashed != "my-secret-password"
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        settings = _make_settings()
        auth = AuthService(settings)
        hashed = auth.hash_password("correct-password")
        assert auth.verify_password("correct-password", hashed) is True

    def test_verify_password_incorrect(self):
        settings = _make_settings()
        auth = AuthService(settings)
        hashed = auth.hash_password("correct-password")
        assert auth.verify_password("wrong-password", hashed) is False

    def test_hash_produces_unique_values(self):
        """Each call to hash_password should produce a different hash (unique salt)."""
        settings = _make_settings()
        auth = AuthService(settings)
        hash1 = auth.hash_password("same-password")
        hash2 = auth.hash_password("same-password")
        assert hash1 != hash2

    def test_verify_works_with_different_hashes_of_same_password(self):
        settings = _make_settings()
        auth = AuthService(settings)
        hash1 = auth.hash_password("same-password")
        hash2 = auth.hash_password("same-password")
        assert auth.verify_password("same-password", hash1) is True
        assert auth.verify_password("same-password", hash2) is True


class TestJWTCreation:
    """AuthService JWT token creation."""

    def test_create_access_token_returns_string(self):
        settings = _make_settings()
        auth = AuthService(settings)
        user_id = uuid.uuid4()
        token = auth.create_access_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_sub_claim(self):
        settings = _make_settings()
        auth = AuthService(settings)
        user_id = uuid.uuid4()
        token = auth.create_access_token(user_id)
        payload = jose_jwt.decode(token, REQUIRED_ENV["JWT_SECRET"], algorithms=["HS256"])
        assert payload["sub"] == str(user_id)

    def test_create_access_token_contains_exp_claim(self):
        settings = _make_settings()
        auth = AuthService(settings)
        user_id = uuid.uuid4()
        token = auth.create_access_token(user_id)
        payload = jose_jwt.decode(token, REQUIRED_ENV["JWT_SECRET"], algorithms=["HS256"])
        assert "exp" in payload

    def test_create_access_token_uses_configured_expiry(self):
        settings = _make_settings(JWT_EXPIRY_MINUTES="30")
        auth = AuthService(settings)
        user_id = uuid.uuid4()
        before = datetime.now(timezone.utc)
        token = auth.create_access_token(user_id)
        after = datetime.now(timezone.utc)

        payload = jose_jwt.decode(token, REQUIRED_ENV["JWT_SECRET"], algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        # JWT exp is integer seconds, so allow 1 second tolerance
        expected_min = before + timedelta(minutes=30) - timedelta(seconds=1)
        expected_max = after + timedelta(minutes=30) + timedelta(seconds=1)
        assert expected_min <= exp <= expected_max

    def test_create_access_token_default_expiry_60_minutes(self):
        settings = _make_settings()
        auth = AuthService(settings)
        user_id = uuid.uuid4()
        before = datetime.now(timezone.utc)
        token = auth.create_access_token(user_id)

        payload = jose_jwt.decode(token, REQUIRED_ENV["JWT_SECRET"], algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        expected_min = before + timedelta(minutes=59, seconds=59)
        expected_max = before + timedelta(minutes=60, seconds=1)
        assert expected_min <= exp <= expected_max


class TestJWTDecoding:
    """AuthService JWT token decoding and validation."""

    def test_decode_valid_token(self):
        settings = _make_settings()
        auth = AuthService(settings)
        user_id = uuid.uuid4()
        token = auth.create_access_token(user_id)
        payload = auth.decode_token(token)
        assert isinstance(payload, TokenPayload)
        assert payload.sub == str(user_id)

    def test_decode_expired_token_raises(self):
        settings = _make_settings()
        auth = AuthService(settings)
        # Create a token that expired 1 hour ago
        expired_payload = {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jose_jwt.encode(expired_payload, REQUIRED_ENV["JWT_SECRET"], algorithm="HS256")
        from jose import JWTError

        with pytest.raises(JWTError):
            auth.decode_token(token)

    def test_decode_token_wrong_secret_raises(self):
        settings = _make_settings()
        auth = AuthService(settings)
        # Create token with a different secret
        payload = {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jose_jwt.encode(payload, "wrong-secret", algorithm="HS256")
        from jose import JWTError

        with pytest.raises(JWTError):
            auth.decode_token(token)

    def test_decode_malformed_token_raises(self):
        settings = _make_settings()
        auth = AuthService(settings)
        from jose import JWTError

        with pytest.raises(JWTError):
            auth.decode_token("not-a-valid-jwt-token")

    def test_decode_token_missing_sub_raises(self):
        settings = _make_settings()
        auth = AuthService(settings)
        # Create token without sub claim
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jose_jwt.encode(payload, REQUIRED_ENV["JWT_SECRET"], algorithm="HS256")
        from jose import JWTError

        with pytest.raises(JWTError, match="sub"):
            auth.decode_token(token)


class TestGetCurrentUser:
    """get_current_user FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        settings = _make_settings()
        auth = AuthService(settings)
        user_id = uuid.uuid4()
        token = auth.create_access_token(user_id)

        # Mock the user returned from DB
        mock_user = MagicMock()
        mock_user.id = user_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        user = await get_current_user(token=token, db=mock_db, settings=settings)
        assert user.id == user_id

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        settings = _make_settings()
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="invalid-token", db=mock_db, settings=settings)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self):
        settings = _make_settings()
        expired_payload = {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jose_jwt.encode(expired_payload, REQUIRED_ENV["JWT_SECRET"], algorithm="HS256")
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=mock_db, settings=settings)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self):
        settings = _make_settings()
        auth = AuthService(settings)
        user_id = uuid.uuid4()
        token = auth.create_access_token(user_id)

        # DB returns no user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=mock_db, settings=settings)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_401_includes_www_authenticate_header(self):
        settings = _make_settings()
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="bad-token", db=mock_db, settings=settings)
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.asyncio
    async def test_token_with_invalid_uuid_raises_401(self):
        settings = _make_settings()
        # Create token with non-UUID sub claim
        payload = {
            "sub": "not-a-uuid",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jose_jwt.encode(payload, REQUIRED_ENV["JWT_SECRET"], algorithm="HS256")
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=mock_db, settings=settings)
        assert exc_info.value.status_code == 401
