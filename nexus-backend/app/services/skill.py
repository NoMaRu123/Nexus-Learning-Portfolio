"""Skill CRUD service.

Encapsulates business logic for creating, listing, updating,
and deleting SkillRecords for a given user.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import SkillRecord
from app.schemas.skill import SkillCreate, SkillUpdate
from app.services.exceptions import DuplicateSkillError, SkillNotFoundError

if TYPE_CHECKING:
    from app.webhooks.service import WebhookService

logger = logging.getLogger(__name__)


class SkillService:
    """Service handling skill CRUD operations for a single user."""

    def __init__(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        webhook_service: WebhookService | None = None,
    ) -> None:
        self._db = db
        self._user_id = user_id
        self._webhook_service = webhook_service

    async def create(self, data: SkillCreate) -> SkillRecord:
        """Create a new skill after validating name uniqueness.

        Args:
            data: Validated skill creation payload.

        Returns:
            The newly created SkillRecord.

        Raises:
            DuplicateSkillError: If a skill with the same name already exists for this user.
        """
        existing = await self._db.execute(
            select(SkillRecord).where(
                SkillRecord.user_id == self._user_id,
                SkillRecord.name == data.name,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateSkillError(data.name)

        skill = SkillRecord(
            user_id=self._user_id,
            name=data.name,
            category=data.category,
            proficiency_level=data.proficiency_level.value,
        )
        self._db.add(skill)
        await self._db.flush()
        await self._db.refresh(skill)
        return skill

    async def list_all(self) -> list[SkillRecord]:
        """Return all skills for the user, sorted alphabetically by name."""
        result = await self._db.execute(
            select(SkillRecord)
            .where(SkillRecord.user_id == self._user_id)
            .order_by(SkillRecord.name.asc())
        )
        return list(result.scalars().all())

    async def update(self, skill_id: uuid.UUID, data: SkillUpdate) -> SkillRecord:
        """Update an existing skill with only the provided (non-None) fields.

        Args:
            skill_id: The UUID of the skill to update.
            data: Validated update payload with optional fields.

        Returns:
            The updated SkillRecord.

        Raises:
            SkillNotFoundError: If no skill matches the id and user_id.
            DuplicateSkillError: If the new name conflicts with another skill.
        """
        skill = await self._get_skill_or_raise(skill_id)

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)

        # Track whether proficiency_level is changing for webhook dispatch
        old_proficiency = skill.proficiency_level
        proficiency_changed = False

        # If renaming, check for duplicate name
        if "name" in update_data and update_data["name"] != skill.name:
            existing = await self._db.execute(
                select(SkillRecord).where(
                    SkillRecord.user_id == self._user_id,
                    SkillRecord.name == update_data["name"],
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateSkillError(update_data["name"])

        for field, value in update_data.items():
            # Convert enum to its string value for proficiency_level
            if field == "proficiency_level" and hasattr(value, "value"):
                value = value.value
            if field == "proficiency_level" and value != old_proficiency:
                proficiency_changed = True
            setattr(skill, field, value)

        await self._db.flush()
        await self._db.refresh(skill)

        if proficiency_changed and self._webhook_service is not None:
            await self._webhook_service.dispatch(
                "skill.proficiency_changed",
                {
                    "id": str(skill.id),
                    "name": skill.name,
                    "old_proficiency_level": old_proficiency,
                    "new_proficiency_level": skill.proficiency_level,
                },
            )

        return skill

    async def delete(self, skill_id: uuid.UUID) -> None:
        """Delete a skill. Cascade deletes learning entries via DB constraint.

        Args:
            skill_id: The UUID of the skill to delete.

        Raises:
            SkillNotFoundError: If no skill matches the id and user_id.
        """
        skill = await self._get_skill_or_raise(skill_id)
        await self._db.delete(skill)
        await self._db.flush()

    async def _get_skill_or_raise(self, skill_id: uuid.UUID) -> SkillRecord:
        """Fetch a skill by id and user_id, or raise SkillNotFoundError."""
        result = await self._db.execute(
            select(SkillRecord).where(
                SkillRecord.id == skill_id,
                SkillRecord.user_id == self._user_id,
            )
        )
        skill = result.scalar_one_or_none()
        if skill is None:
            raise SkillNotFoundError(str(skill_id))
        return skill
