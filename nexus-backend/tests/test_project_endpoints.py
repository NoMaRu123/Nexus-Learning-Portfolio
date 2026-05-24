"""Tests for app.api.projects module.

Validates project CRUD endpoints using mocked database sessions and services.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.projects import create_project, delete_project, list_projects, update_project
from app.models.project import ProjectRecord
from app.models.user import UserAccount
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectStatus, ProjectUpdate
from app.services.exceptions import ProjectNotFoundError


def _make_user(user_id: uuid.UUID | None = None) -> UserAccount:
    """Factory for creating a mock UserAccount."""
    user = MagicMock(spec=UserAccount)
    user.id = user_id or uuid.uuid4()
    user.email = "test@example.com"
    return user


def _make_project_record(
    user_id: uuid.UUID,
    name: str = "My Project",
    description: str | None = "A test project",
    status: str = "in_progress",
    technology_tags: list[str] | None = None,
    project_id: uuid.UUID | None = None,
) -> ProjectRecord:
    """Factory for creating ProjectRecord instances for testing."""
    return ProjectRecord(
        id=project_id or uuid.uuid4(),
        user_id=user_id,
        name=name,
        description=description,
        status=status,
        technology_tags=technology_tags or ["Python", "FastAPI"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestListProjects:
    """GET /api/projects endpoint tests."""

    @pytest.mark.asyncio
    async def test_list_projects_returns_wrapped_response(self):
        """Listing projects returns an ApiResponse wrapping a list of ProjectResponse."""
        user = _make_user()
        projects = [
            _make_project_record(user.id, name="Project B"),
            _make_project_record(user.id, name="Project A"),
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = projects

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        response = await list_projects(current_user=user, db=mock_db)

        assert len(response.data) == 2
        assert all(isinstance(p, ProjectResponse) for p in response.data)
        assert response.data[0].name == "Project B"
        assert response.data[1].name == "Project A"

    @pytest.mark.asyncio
    async def test_list_projects_empty_returns_empty_list(self):
        """Listing projects when user has none returns an empty data list."""
        user = _make_user()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        response = await list_projects(current_user=user, db=mock_db)

        assert response.data == []


class TestCreateProject:
    """POST /api/projects endpoint tests."""

    @pytest.mark.asyncio
    async def test_create_project_returns_wrapped_response(self):
        """Creating a project returns an ApiResponse wrapping a ProjectResponse."""
        user = _make_user()
        data = ProjectCreate(
            name="New Project",
            description="A new project",
            status=ProjectStatus.planning,
            technology_tags=["React", "TypeScript"],
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        async def mock_refresh(obj: ProjectRecord) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        response = await create_project(data=data, current_user=user, db=mock_db)

        assert isinstance(response.data, ProjectResponse)
        assert response.data.name == "New Project"
        assert response.data.description == "A new project"
        assert response.data.status == "planning"
        assert response.data.technology_tags == ["React", "TypeScript"]

    @pytest.mark.asyncio
    async def test_create_project_with_defaults(self):
        """Creating a project with minimal fields uses default values."""
        user = _make_user()
        data = ProjectCreate(name="Minimal Project")

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        async def mock_refresh(obj: ProjectRecord) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        response = await create_project(data=data, current_user=user, db=mock_db)

        assert isinstance(response.data, ProjectResponse)
        assert response.data.name == "Minimal Project"
        assert response.data.status == "in_progress"
        assert response.data.technology_tags == []


class TestUpdateProject:
    """PUT /api/projects/{id} endpoint tests."""

    @pytest.mark.asyncio
    async def test_update_project_returns_wrapped_response(self):
        """Updating a project returns an ApiResponse wrapping the updated ProjectResponse."""
        user = _make_user()
        project_id = uuid.uuid4()
        existing = _make_project_record(user.id, name="Old Name", project_id=project_id)
        data = ProjectUpdate(name="New Name", status=ProjectStatus.completed)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj: ProjectRecord) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        response = await update_project(project_id=project_id, data=data, current_user=user, db=mock_db)

        assert isinstance(response.data, ProjectResponse)
        assert response.data.name == "New Name"

    @pytest.mark.asyncio
    async def test_update_nonexistent_project_returns_404(self):
        """Updating a project that doesn't exist raises 404 Not Found."""
        user = _make_user()
        project_id = uuid.uuid4()
        data = ProjectUpdate(name="Updated Name")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await update_project(project_id=project_id, data=data, current_user=user, db=mock_db)

        assert exc_info.value.status_code == 404


class TestDeleteProject:
    """DELETE /api/projects/{id} endpoint tests."""

    @pytest.mark.asyncio
    async def test_delete_project_returns_204(self):
        """Deleting an existing project returns a 204 No Content response."""
        user = _make_user()
        project_id = uuid.uuid4()
        existing = _make_project_record(user.id, name="To Delete", project_id=project_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        response = await delete_project(project_id=project_id, current_user=user, db=mock_db)

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_nonexistent_project_returns_404(self):
        """Deleting a project that doesn't exist raises 404 Not Found."""
        user = _make_user()
        project_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await delete_project(project_id=project_id, current_user=user, db=mock_db)

        assert exc_info.value.status_code == 404
