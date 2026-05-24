"""Learning entry service.

Encapsulates business logic for creating and listing
LearningEntries linked to skills or projects for a given user.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import LearningEntry
from app.models.project import ProjectRecord
from app.models.skill import SkillRecord
from app.schemas.entry import EntryCreate
from app.services.exceptions import EntryParentNotFoundError


class LearningEntryService:
    """Service handling learning entry operations for a single user."""

    def __init__(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        self._db = db
        self._user_id = user_id

    async def create(self, data: EntryCreate) -> LearningEntry:
        """Create a new learning entry after validating the parent reference.

        Args:
            data: Validated entry creation payload with exactly one of
                  skill_id or project_id set.

        Returns:
            The newly created LearningEntry.

        Raises:
            EntryParentNotFoundError: If the referenced skill or project
                does not exist for this user.
        """
        if data.skill_id is not None:
            await self._validate_skill_exists(data.skill_id)
        else:
            await self._validate_project_exists(data.project_id)  # type: ignore[arg-type]

        entry = LearningEntry(
            user_id=self._user_id,
            skill_id=data.skill_id,
            project_id=data.project_id,
            description=data.description,
            entry_metadata=data.metadata,
        )
        self._db.add(entry)
        await self._db.flush()
        await self._db.refresh(entry)
        return entry

    async def list_by_skill(
        self,
        skill_id: uuid.UUID,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[LearningEntry], int]:
        """Return paginated entries for a skill, sorted by timestamp descending.

        Args:
            skill_id: The UUID of the skill to list entries for.
            page: Page number (1-indexed).
            size: Number of entries per page.

        Returns:
            A tuple of (entries, total_count).

        Raises:
            EntryParentNotFoundError: If the skill does not exist for this user.
        """
        await self._validate_skill_exists(skill_id)
        return await self._list_entries(
            filter_column=LearningEntry.skill_id,
            parent_id=skill_id,
            page=page,
            size=size,
        )

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[LearningEntry], int]:
        """Return paginated entries for a project, sorted by timestamp descending.

        Args:
            project_id: The UUID of the project to list entries for.
            page: Page number (1-indexed).
            size: Number of entries per page.

        Returns:
            A tuple of (entries, total_count).

        Raises:
            EntryParentNotFoundError: If the project does not exist for this user.
        """
        await self._validate_project_exists(project_id)
        return await self._list_entries(
            filter_column=LearningEntry.project_id,
            parent_id=project_id,
            page=page,
            size=size,
        )

    async def _list_entries(
        self,
        filter_column: object,
        parent_id: uuid.UUID,
        page: int,
        size: int,
    ) -> tuple[list[LearningEntry], int]:
        """Shared pagination logic for listing entries by parent."""
        offset = (page - 1) * size

        # Get total count
        count_result = await self._db.execute(
            select(func.count()).select_from(LearningEntry).where(
                filter_column == parent_id,  # type: ignore[arg-type]
            )
        )
        total = count_result.scalar_one()

        # Get paginated entries
        result = await self._db.execute(
            select(LearningEntry)
            .where(filter_column == parent_id)  # type: ignore[arg-type]
            .order_by(LearningEntry.timestamp.desc())
            .offset(offset)
            .limit(size)
        )
        entries = list(result.scalars().all())

        return entries, total

    async def _validate_skill_exists(self, skill_id: uuid.UUID) -> None:
        """Verify a skill exists for this user, or raise EntryParentNotFoundError."""
        result = await self._db.execute(
            select(SkillRecord.id).where(
                SkillRecord.id == skill_id,
                SkillRecord.user_id == self._user_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise EntryParentNotFoundError("Skill", str(skill_id))

    async def _validate_project_exists(self, project_id: uuid.UUID) -> None:
        """Verify a project exists for this user, or raise EntryParentNotFoundError."""
        result = await self._db.execute(
            select(ProjectRecord.id).where(
                ProjectRecord.id == project_id,
                ProjectRecord.user_id == self._user_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise EntryParentNotFoundError("Project", str(project_id))
