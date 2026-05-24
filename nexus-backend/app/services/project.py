"""Project CRUD service.

Encapsulates business logic for creating, listing, updating,
and deleting ProjectRecords for a given user.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectRecord
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.exceptions import ProjectNotFoundError

if TYPE_CHECKING:
    from app.webhooks.service import WebhookService

logger = logging.getLogger(__name__)


class ProjectService:
    """Service handling project CRUD operations for a single user."""

    def __init__(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        webhook_service: WebhookService | None = None,
    ) -> None:
        self._db = db
        self._user_id = user_id
        self._webhook_service = webhook_service

    async def create(self, data: ProjectCreate) -> ProjectRecord:
        """Create a new project.

        Args:
            data: Validated project creation payload.

        Returns:
            The newly created ProjectRecord.
        """
        project = ProjectRecord(
            user_id=self._user_id,
            name=data.name,
            description=data.description,
            status=data.status.value,
            technology_tags=data.technology_tags,
        )
        self._db.add(project)
        await self._db.flush()
        await self._db.refresh(project)

        if self._webhook_service is not None:
            await self._webhook_service.dispatch(
                "project.created",
                {
                    "id": str(project.id),
                    "name": project.name,
                    "status": project.status,
                    "technology_tags": project.technology_tags,
                },
            )

        return project

    async def list_all(self) -> list[ProjectRecord]:
        """Return all projects for the user, sorted by created_at descending."""
        result = await self._db.execute(
            select(ProjectRecord)
            .where(ProjectRecord.user_id == self._user_id)
            .order_by(ProjectRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(
        self, project_id: uuid.UUID, data: ProjectUpdate
    ) -> ProjectRecord:
        """Update an existing project with only the provided (non-None) fields.

        Args:
            project_id: The UUID of the project to update.
            data: Validated update payload with optional fields.

        Returns:
            The updated ProjectRecord.

        Raises:
            ProjectNotFoundError: If no project matches the id and user_id.
        """
        project = await self._get_project_or_raise(project_id)

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)

        for field, value in update_data.items():
            # Convert enum to its string value for status
            if field == "status" and hasattr(value, "value"):
                value = value.value
            setattr(project, field, value)

        await self._db.flush()
        await self._db.refresh(project)
        return project

    async def delete(self, project_id: uuid.UUID) -> None:
        """Delete a project. Cascade deletes learning entries via DB constraint.

        Args:
            project_id: The UUID of the project to delete.

        Raises:
            ProjectNotFoundError: If no project matches the id and user_id.
        """
        project = await self._get_project_or_raise(project_id)
        await self._db.delete(project)
        await self._db.flush()

    async def _get_project_or_raise(self, project_id: uuid.UUID) -> ProjectRecord:
        """Fetch a project by id and user_id, or raise ProjectNotFoundError."""
        result = await self._db.execute(
            select(ProjectRecord).where(
                ProjectRecord.id == project_id,
                ProjectRecord.user_id == self._user_id,
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ProjectNotFoundError(str(project_id))
        return project
