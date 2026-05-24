"""Pydantic schemas for learning entry endpoints.

Defines request and response models for learning entry operations,
with a validator ensuring exactly one parent reference (skill or project).
"""

import uuid
from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class EntryCreate(BaseModel):
    """Request body for creating a learning entry.

    Exactly one of skill_id or project_id must be provided.
    """

    skill_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    description: str
    metadata: dict | None = None

    @model_validator(mode="after")
    def validate_single_parent(self) -> "EntryCreate":
        """Ensure exactly one of skill_id or project_id is set."""
        has_skill = self.skill_id is not None
        has_project = self.project_id is not None
        if has_skill == has_project:
            raise ValueError("Exactly one of skill_id or project_id must be provided")
        return self


class LearningEntryResponse(BaseModel):
    """Response body for a learning entry record."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    skill_id: uuid.UUID | None
    project_id: uuid.UUID | None
    description: str
    metadata: dict | None = Field(
        validation_alias=AliasChoices("entry_metadata", "metadata")
    )
    timestamp: datetime
