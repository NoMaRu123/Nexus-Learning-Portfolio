"""Pydantic schemas for authentication endpoints.

Defines request and response models for user registration and login.
"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response body containing a JWT access token."""

    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    """Response body confirming successful registration."""

    message: str
    user_id: str
