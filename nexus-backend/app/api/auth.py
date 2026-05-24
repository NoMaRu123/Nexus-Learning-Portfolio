"""Authentication API endpoints.

Provides user registration and login routes with JWT-based authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import AuthService, get_auth_service
from app.models.profile import UserProfile
from app.models.user import UserAccount
from app.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    """Register a new user account.

    Creates a UserAccount with a hashed password and a default empty
    UserProfile in the same transaction. Returns a confirmation response.

    Raises:
        HTTPException 409: If the email is already registered.
    """
    # Check for duplicate email
    result = await db.execute(
        select(UserAccount).where(UserAccount.email == request.email)
    )
    existing_user = result.scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{request.email}' already exists",
        )

    # Hash password and create user account
    hashed_password = auth_service.hash_password(request.password)
    user = UserAccount(
        email=request.email,
        hashed_password=hashed_password,
    )
    db.add(user)
    await db.flush()

    # Create default empty profile
    profile = UserProfile(user_id=user.id)
    db.add(profile)

    return RegisterResponse(
        message="User registered successfully",
        user_id=str(user.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate a user and return a JWT access token.

    Verifies the email and password against stored credentials.
    Returns a generic error message on failure without revealing
    which field was incorrect.

    Raises:
        HTTPException 401: If credentials are invalid.
    """
    # Look up user by email
    result = await db.execute(
        select(UserAccount).where(UserAccount.email == request.email)
    )
    user = result.scalar_one_or_none()

    # Verify password — use generic error for both missing user and wrong password
    if user is None or not auth_service.verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate and return JWT
    access_token = auth_service.create_access_token(user.id)
    return TokenResponse(access_token=access_token)
