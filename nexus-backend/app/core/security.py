"""Authentication service and JWT utilities.

Provides password hashing via bcrypt, JWT creation/validation via
python-jose with HS256, and a FastAPI dependency for extracting
the current authenticated user from the Authorization header.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt_module
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.user import UserAccount

logger = logging.getLogger(__name__)

# HS256 is the only supported algorithm per security requirements
_ALGORITHM = "HS256"

# OAuth2 scheme extracts Bearer token from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str
    exp: datetime


class AuthService:
    """Handles password hashing and JWT token operations.

    Uses bcrypt for password hashing and python-jose with HS256
    for JWT creation and validation.
    """

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret
        self._expiry_minutes = settings.jwt_expiry_minutes

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password using bcrypt.

        Args:
            password: The plaintext password to hash.

        Returns:
            The bcrypt-hashed password string.
        """
        salt = _bcrypt_module.gensalt()
        hashed = _bcrypt_module.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a bcrypt hash.

        Args:
            plain_password: The plaintext password to check.
            hashed_password: The stored bcrypt hash.

        Returns:
            True if the password matches, False otherwise.
        """
        return _bcrypt_module.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )

    def create_access_token(self, user_id: uuid.UUID) -> str:
        """Create a JWT access token for the given user.

        Token payload contains the user ID as the `sub` claim and
        an expiry timestamp based on JWT_EXPIRY_MINUTES.

        Args:
            user_id: The UUID of the authenticated user.

        Returns:
            The encoded JWT string.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self._expiry_minutes)
        payload = {
            "sub": str(user_id),
            "exp": expire,
        }
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM)

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT access token.

        Args:
            token: The encoded JWT string.

        Returns:
            The decoded TokenPayload with sub and exp claims.

        Raises:
            JWTError: If the token is invalid, expired, or malformed.
        """
        payload = jwt.decode(token, self._secret, algorithms=[_ALGORITHM])
        sub = payload.get("sub")
        exp = payload.get("exp")
        if sub is None:
            raise JWTError("Token missing 'sub' claim")
        return TokenPayload(sub=sub, exp=datetime.fromtimestamp(exp, tz=timezone.utc))


def get_auth_service(settings: Settings = Depends(get_settings)) -> AuthService:
    """FastAPI dependency that provides an AuthService instance."""
    return AuthService(settings)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserAccount:
    """FastAPI dependency that extracts and validates the current user from JWT.

    Extracts the Bearer token from the Authorization header, decodes it,
    looks up the user by ID from the token's `sub` claim, and returns
    the UserAccount. Returns 401 for any authentication failure.

    Args:
        token: The Bearer token extracted by OAuth2PasswordBearer.
        db: The async database session.
        settings: Application settings for JWT configuration.

    Returns:
        The authenticated UserAccount.

    Raises:
        HTTPException: 401 if the token is missing, invalid, expired,
            or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        auth_service = AuthService(settings)
        payload = auth_service.decode_token(token)
        user_id = uuid.UUID(payload.sub)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(UserAccount).where(UserAccount.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user
