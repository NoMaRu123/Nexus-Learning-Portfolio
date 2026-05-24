"""Tests for app.api.entries module.

Validates learning entry list and create endpoints using mocked
database sessions and services.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.entries import create_entry, list_entries
from app.models.entry import LearningEntry
from app.models.user import UserAccount
from app.schemas.entry import EntryCreate, LearningEntryResponse


def _make_user(user_id: uuid.UUID | None = None) -> UserAccount:
    """Factory for creating a mock UserAccount."""
    user = MagicMock(spec=UserAccount)
    user.id = user_id or uuid.uuid4()
    user.email = "test@example.com"
    return user


def _make_entry_obj(
    user_id: uuid.UUID,
    skill_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    description: str = "Learned something new",
    entry_id: uuid.UUID | None = None,
    entry_metadata: dict | None = None,
) -> SimpleNamespace:
    """Factory for creating entry-like objects for testing.

    Uses SimpleNamespace to avoid SQLAlchemy instrumented attribute
    issues with JSONB columns returning MetaData sentinels.
    """
    return SimpleNamespace(
        id=entry_id or uuid.uuid4(),
        user_id=user_id,
        skill_id=skill_id,
        project_id=project_id,
        description=description,
        entry_metadata=entry_metadata,
        metadata=entry_metadata,
        timestamp=datetime.now(timezone.utc),
    )


class TestListEntries:
    """GET /api/entries endpoint tests."""

    @pytest.mark.asyncio
    async def test_list_entries_requires_exactly_one_parent(self):
        """Providing neither skill_id nor project_id returns 422."""
        user = _make_user()
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await list_entries(
                skill_id=None,
                project_id=None,
                page=1,
                size=10,
                current_user=user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 422
        assert "Exactly one" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_entries_rejects_both_parents(self):
        """Providing both skill_id and project_id returns 422."""
        user = _make_user()
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await list_entries(
                skill_id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                page=1,
                size=10,
                current_user=user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_list_entries_by_skill_returns_paginated_response(self):
        """Listing entries by skill_id returns a PaginatedResponse."""
        user = _make_user()
        skill_id = uuid.uuid4()
        entries = [
            _make_entry_obj(user.id, skill_id=skill_id, description="Entry 1"),
            _make_entry_obj(user.id, skill_id=skill_id, description="Entry 2"),
        ]

        # Mock DB: skill exists check + count query + entries query
        skill_exists_result = MagicMock()
        skill_exists_result.scalar_one_or_none.return_value = skill_id

        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        entries_scalars = MagicMock()
        entries_scalars.all.return_value = entries
        entries_result = MagicMock()
        entries_result.scalars.return_value = entries_scalars

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [
            skill_exists_result,
            count_result,
            entries_result,
        ]

        response = await list_entries(
            skill_id=skill_id,
            project_id=None,
            page=1,
            size=10,
            current_user=user,
            db=mock_db,
        )

        assert len(response.items) == 2
        assert response.total == 2
        assert response.page == 1
        assert response.size == 10
        assert response.total_pages == 1
        assert all(isinstance(e, LearningEntryResponse) for e in response.items)

    @pytest.mark.asyncio
    async def test_list_entries_by_project_returns_paginated_response(self):
        """Listing entries by project_id returns a PaginatedResponse."""
        user = _make_user()
        project_id = uuid.uuid4()
        entries = [
            _make_entry_obj(user.id, project_id=project_id, description="Entry 1"),
        ]

        project_exists_result = MagicMock()
        project_exists_result.scalar_one_or_none.return_value = project_id

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        entries_scalars = MagicMock()
        entries_scalars.all.return_value = entries
        entries_result = MagicMock()
        entries_result.scalars.return_value = entries_scalars

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [
            project_exists_result,
            count_result,
            entries_result,
        ]

        response = await list_entries(
            skill_id=None,
            project_id=project_id,
            page=1,
            size=10,
            current_user=user,
            db=mock_db,
        )

        assert len(response.items) == 1
        assert response.total == 1
        assert response.page == 1

    @pytest.mark.asyncio
    async def test_list_entries_nonexistent_skill_returns_404(self):
        """Listing entries for a non-existent skill returns 404."""
        user = _make_user()
        skill_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await list_entries(
                skill_id=skill_id,
                project_id=None,
                page=1,
                size=10,
                current_user=user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_entries_pagination_metadata(self):
        """Paginated response includes correct total_pages calculation."""
        user = _make_user()
        skill_id = uuid.uuid4()
        entries = [
            _make_entry_obj(user.id, skill_id=skill_id, description=f"Entry {i}")
            for i in range(5)
        ]

        skill_exists_result = MagicMock()
        skill_exists_result.scalar_one_or_none.return_value = skill_id

        count_result = MagicMock()
        count_result.scalar_one.return_value = 25  # 25 total entries

        entries_scalars = MagicMock()
        entries_scalars.all.return_value = entries
        entries_result = MagicMock()
        entries_result.scalars.return_value = entries_scalars

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [
            skill_exists_result,
            count_result,
            entries_result,
        ]

        response = await list_entries(
            skill_id=skill_id,
            project_id=None,
            page=2,
            size=5,
            current_user=user,
            db=mock_db,
        )

        assert response.total == 25
        assert response.page == 2
        assert response.size == 5
        assert response.total_pages == 5


class TestCreateEntry:
    """POST /api/entries endpoint tests."""

    @pytest.mark.asyncio
    async def test_create_entry_with_skill_returns_wrapped_response(self):
        """Creating an entry linked to a skill returns ApiResponse[LearningEntryResponse]."""
        user = _make_user()
        skill_id = uuid.uuid4()
        data = EntryCreate(
            skill_id=skill_id,
            description="Learned FastAPI routing",
        )

        # Mock DB: skill exists check
        skill_exists_result = MagicMock()
        skill_exists_result.scalar_one_or_none.return_value = skill_id

        mock_db = AsyncMock()
        mock_db.execute.return_value = skill_exists_result
        mock_db.add = MagicMock()

        async def mock_refresh(obj: LearningEntry) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.timestamp = datetime.now(timezone.utc)
            # Force entry_metadata to plain None to avoid JSONB sentinel
            obj.entry_metadata = None

        mock_db.refresh = mock_refresh

        response = await create_entry(data=data, current_user=user, db=mock_db)

        assert isinstance(response.data, LearningEntryResponse)
        assert response.data.description == "Learned FastAPI routing"
        assert response.data.skill_id == skill_id
        assert response.data.project_id is None

    @pytest.mark.asyncio
    async def test_create_entry_with_project_returns_wrapped_response(self):
        """Creating an entry linked to a project returns ApiResponse[LearningEntryResponse]."""
        user = _make_user()
        project_id = uuid.uuid4()
        data = EntryCreate(
            project_id=project_id,
            description="Added CI pipeline",
        )

        project_exists_result = MagicMock()
        project_exists_result.scalar_one_or_none.return_value = project_id

        mock_db = AsyncMock()
        mock_db.execute.return_value = project_exists_result
        mock_db.add = MagicMock()

        async def mock_refresh(obj: LearningEntry) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.timestamp = datetime.now(timezone.utc)
            obj.entry_metadata = None

        mock_db.refresh = mock_refresh

        response = await create_entry(data=data, current_user=user, db=mock_db)

        assert isinstance(response.data, LearningEntryResponse)
        assert response.data.description == "Added CI pipeline"
        assert response.data.project_id == project_id

    @pytest.mark.asyncio
    async def test_create_entry_nonexistent_parent_returns_404(self):
        """Creating an entry referencing a non-existent skill returns 404."""
        user = _make_user()
        skill_id = uuid.uuid4()
        data = EntryCreate(
            skill_id=skill_id,
            description="Some progress",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await create_entry(data=data, current_user=user, db=mock_db)

        assert exc_info.value.status_code == 404
