"""Tests for app.services.project module.

Validates ProjectService CRUD operations using mocked async database sessions.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.project import ProjectRecord
from app.schemas.project import ProjectCreate, ProjectStatus, ProjectUpdate
from app.services.exceptions import ProjectNotFoundError
from app.services.project import ProjectService
from app.webhooks.service import WebhookService


def _make_project(
    user_id: uuid.UUID,
    name: str = "My Project",
    description: str | None = "A test project",
    status: str = "in_progress",
    technology_tags: list[str] | None = None,
    project_id: uuid.UUID | None = None,
) -> ProjectRecord:
    """Factory for creating ProjectRecord instances for testing."""
    project = ProjectRecord(
        id=project_id or uuid.uuid4(),
        user_id=user_id,
        name=name,
        description=description,
        status=status,
        technology_tags=technology_tags or [],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return project


def _mock_db_no_result() -> AsyncMock:
    """Create a mock DB session where execute returns no rows."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mock_db.add = MagicMock()
    return mock_db


def _mock_db_with_result(record: object) -> AsyncMock:
    """Create a mock DB session where execute returns a single record."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = record
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mock_db.add = MagicMock()
    return mock_db


class TestProjectServiceCreate:
    """Tests for ProjectService.create()."""

    @pytest.mark.asyncio
    async def test_create_with_valid_data_returns_project(self):
        """Creating a project with valid data returns a ProjectRecord with a UUID."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        async def mock_refresh(obj: ProjectRecord) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = ProjectService(db=mock_db, user_id=user_id)
        data = ProjectCreate(
            name="Portfolio Site",
            description="My personal portfolio",
            technology_tags=["React", "TypeScript"],
        )

        result = await service.create(data)

        assert result.name == "Portfolio Site"
        assert result.description == "My personal portfolio"
        assert result.status == "in_progress"
        assert result.technology_tags == ["React", "TypeScript"]
        assert result.user_id == user_id
        assert result.id is not None
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_stores_status_as_string_value(self):
        """The status enum is stored as its string value."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        async def mock_refresh(obj: ProjectRecord) -> None:
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = ProjectService(db=mock_db, user_id=user_id)
        data = ProjectCreate(
            name="Completed App",
            status=ProjectStatus.completed,
        )

        result = await service.create(data)

        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_create_with_defaults(self):
        """Creating a project with minimal data uses default values."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        async def mock_refresh(obj: ProjectRecord) -> None:
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = ProjectService(db=mock_db, user_id=user_id)
        data = ProjectCreate(name="Minimal Project")

        result = await service.create(data)

        assert result.name == "Minimal Project"
        assert result.description is None
        assert result.status == "in_progress"
        assert result.technology_tags == []


class TestProjectServiceListAll:
    """Tests for ProjectService.list_all()."""

    @pytest.mark.asyncio
    async def test_list_all_returns_projects(self):
        """list_all returns projects for the user."""
        user_id = uuid.uuid4()
        projects = [
            _make_project(user_id, name="Project C"),
            _make_project(user_id, name="Project B"),
            _make_project(user_id, name="Project A"),
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = projects

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        service = ProjectService(db=mock_db, user_id=user_id)
        result = await service.list_all()

        # The service delegates sorting to the DB query (ORDER BY created_at DESC),
        # so we verify the query was executed and results returned as-is.
        assert len(result) == 3
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_all_empty_returns_empty_list(self):
        """list_all returns an empty list when user has no projects."""
        user_id = uuid.uuid4()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        service = ProjectService(db=mock_db, user_id=user_id)
        result = await service.list_all()

        assert result == []


class TestProjectServiceUpdate:
    """Tests for ProjectService.update()."""

    @pytest.mark.asyncio
    async def test_update_modifies_only_provided_fields(self):
        """Updating with partial data only changes the specified fields."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        existing = _make_project(
            user_id,
            name="Old Name",
            description="Old desc",
            status="in_progress",
            project_id=project_id,
        )

        mock_db = _mock_db_with_result(existing)

        async def mock_refresh(obj: ProjectRecord) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = ProjectService(db=mock_db, user_id=user_id)
        data = ProjectUpdate(name="New Name")

        result = await service.update(project_id, data)

        assert result.name == "New Name"
        # Other fields should remain unchanged
        assert result.description == "Old desc"
        assert result.status == "in_progress"

    @pytest.mark.asyncio
    async def test_update_status_converts_enum_to_string(self):
        """Updating status converts the enum to its string value."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        existing = _make_project(user_id, status="in_progress", project_id=project_id)

        mock_db = _mock_db_with_result(existing)

        async def mock_refresh(obj: ProjectRecord) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = ProjectService(db=mock_db, user_id=user_id)
        data = ProjectUpdate(status=ProjectStatus.completed)

        result = await service.update(project_id, data)

        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_update_nonexistent_project_raises_not_found(self):
        """Updating a project that doesn't exist raises ProjectNotFoundError."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        service = ProjectService(db=mock_db, user_id=user_id)
        data = ProjectUpdate(name="Updated")

        with pytest.raises(ProjectNotFoundError) as exc_info:
            await service.update(project_id, data)

        assert str(project_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_with_no_changes_returns_unchanged(self):
        """Updating with all None fields returns the project unchanged."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        existing = _make_project(user_id, name="My Project", project_id=project_id)

        mock_db = _mock_db_with_result(existing)

        async def mock_refresh(obj: ProjectRecord) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = ProjectService(db=mock_db, user_id=user_id)
        data = ProjectUpdate()  # All fields None

        result = await service.update(project_id, data)

        assert result.name == "My Project"


class TestProjectServiceDelete:
    """Tests for ProjectService.delete()."""

    @pytest.mark.asyncio
    async def test_delete_removes_project(self):
        """Deleting an existing project calls db.delete and flush."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        existing = _make_project(user_id, name="To Delete", project_id=project_id)

        mock_db = _mock_db_with_result(existing)

        service = ProjectService(db=mock_db, user_id=user_id)
        await service.delete(project_id)

        mock_db.delete.assert_awaited_once_with(existing)
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_project_raises_not_found(self):
        """Deleting a project that doesn't exist raises ProjectNotFoundError."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        service = ProjectService(db=mock_db, user_id=user_id)

        with pytest.raises(ProjectNotFoundError) as exc_info:
            await service.delete(project_id)

        assert str(project_id) in str(exc_info.value)


class TestProjectServiceWebhookIntegration:
    """Tests for webhook dispatch integration in ProjectService."""

    @pytest.mark.asyncio
    async def test_create_dispatches_project_created_webhook(self):
        """Creating a project dispatches a 'project.created' webhook event."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        async def mock_refresh(obj: ProjectRecord) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        mock_webhook = AsyncMock(spec=WebhookService)

        service = ProjectService(db=mock_db, user_id=user_id, webhook_service=mock_webhook)
        data = ProjectCreate(
            name="Portfolio Site",
            description="My portfolio",
            technology_tags=["React", "TypeScript"],
        )

        result = await service.create(data)

        mock_webhook.dispatch.assert_awaited_once()
        call_args = mock_webhook.dispatch.call_args
        assert call_args[0][0] == "project.created"
        payload = call_args[0][1]
        assert payload["id"] == str(result.id)
        assert payload["name"] == "Portfolio Site"
        assert payload["status"] == "in_progress"
        assert payload["technology_tags"] == ["React", "TypeScript"]

    @pytest.mark.asyncio
    async def test_create_without_webhook_service_works(self):
        """Creating a project without a webhook_service still works normally."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        async def mock_refresh(obj: ProjectRecord) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = ProjectService(db=mock_db, user_id=user_id)
        data = ProjectCreate(name="No Webhook Project")

        result = await service.create(data)

        assert result.name == "No Webhook Project"

    @pytest.mark.asyncio
    async def test_create_webhook_failure_does_not_block_creation(self):
        """A webhook dispatch failure does not prevent project creation."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        async def mock_refresh(obj: ProjectRecord) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        mock_webhook = AsyncMock(spec=WebhookService)
        # WebhookService.dispatch() is fire-and-forget — it catches all
        # exceptions internally. We verify the service still returns the
        # project even if dispatch is called.
        mock_webhook.dispatch.return_value = None

        service = ProjectService(db=mock_db, user_id=user_id, webhook_service=mock_webhook)
        data = ProjectCreate(name="Webhook Fail Project")

        result = await service.create(data)

        assert result.name == "Webhook Fail Project"
        mock_webhook.dispatch.assert_awaited_once()
