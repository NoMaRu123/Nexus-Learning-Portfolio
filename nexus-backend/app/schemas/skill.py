"""Pydantic schemas for skill endpoints.

Defines request and response models for skill CRUD operations,
including an enum for proficiency levels.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ProficiencyLevel(str, Enum):
    """Valid proficiency levels for a skill."""

    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class SkillCreate(BaseModel):
    """Request body for creating a new skill."""

    name: str
    category: str
    proficiency_level: ProficiencyLevel = ProficiencyLevel.beginner


class SkillUpdate(BaseModel):
    """Request body for updating an existing skill. All fields optional."""

    name: str | None = None
    category: str | None = None
    proficiency_level: ProficiencyLevel | None = None


class SkillResponse(BaseModel):
    """Response body for a skill record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    proficiency_level: str
    created_at: datetime
    updated_at: datetime
