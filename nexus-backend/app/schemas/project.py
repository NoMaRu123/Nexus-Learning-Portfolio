"""Pydantic schemas for project endpoints.

Defines request and response models for project CRUD operations,
including an enum for project status values.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ProjectStatus(str, Enum):
    """Valid status values for a project."""

    planning = "planning"
    in_progress = "in_progress"
    completed = "completed"
    archived = "archived"


class ProjectCreate(BaseModel):
    """Request body for creating a new project."""

    name: str
    description: str | None = None
    status: ProjectStatus = ProjectStatus.in_progress
    technology_tags: list[str] = []


class ProjectUpdate(BaseModel):
    """Request body for updating an existing project. All fields optional."""

    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    technology_tags: list[str] | None = None


class ProjectResponse(BaseModel):
    """Response body for a project record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    status: str
    technology_tags: list[str]
    created_at: datetime
    updated_at: datetime
