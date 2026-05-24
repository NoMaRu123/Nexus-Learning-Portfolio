"""Pydantic schemas for user profile endpoints.

Defines request and response models for profile management,
including separate schemas for authenticated and public profile views.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ProfileUpdate(BaseModel):
    """Request body for updating a user profile. All fields optional."""

    name: str | None = None
    bio: str | None = None
    contact_email: EmailStr | None = None
    social_links: dict | None = None


class UserProfileResponse(BaseModel):
    """Full profile response for the authenticated user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str | None
    bio: str | None
    contact_email: str | None
    social_links: dict | None
    picture_url: str | None
    updated_at: datetime


class PublicProfileResponse(BaseModel):
    """Public-facing profile response excluding private fields."""

    model_config = ConfigDict(from_attributes=True)

    name: str | None
    bio: str | None
    contact_email: str | None
    social_links: dict | None
    picture_url: str | None
