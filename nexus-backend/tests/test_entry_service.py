"""Tests for app.services.entry module.

Validates LearningEntryService operations using mocked async database sessions.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.entry import LearningEntry
from app.schemas.entry import EntryCreate
from app.services.entry import LearningEntryService
from app.services.exceptions import EntryParentNotFoundError


def _make_entry(
    user_id: uuid.UUID,
    skill_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    description: str = "Learned something new",
    entry_metadata: dict | None = None,
    entry_id: uuid.UUID | None = None,
) -> LearningEntry:
    """Factory for creating LearningEntry instances for testing."""
    entry = LearningEntry(
        id=entry_id or uuid.uuid4(),
        user_id=user_id,
        skill_id=skill_id,
        project_id=project_id,
        description=description,
        entry_metadata=entry_metadata,
        timestamp=datetime.now(timezone.utc),
    )
    return entry


def _mock_db_validate_found() -> AsyncMock:
    """Create a mock DB where the first execute (validation) finds the parent."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = uuid.uuid4()  # parent exists
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mock_db.add = MagicMock()
    return mock_db


def _mock_db_validate_not_found() -> AsyncMock:
    """Create a mock DB where the first execute (validation) finds no parent."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mock_db.add = MagicMock()
    return mock_db


class TestLearningEntryServiceCreate:
    """Tests for LearningEntryService.create()."""

    @pytest.mark.asyncio
    async def test_create_with_valid_skill_reference(self):
        """Creating an entry with a valid skill_id returns a LearningEntry."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        mock_db = _mock_db_validate_found()

        async def mock_refresh(obj: LearningEntry) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.timestamp = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = LearningEntryService(db=mock_db, user_id=user_id)
        data = EntryCreate(
            skill_id=skill_id,
            description="Completed Python tutorial",
        )

        result = await service.create(data)

        assert result.description == "Completed Python tutorial"
        assert result.skill_id == skill_id
        assert result.project_id is None
        assert result.user_id == user_id
        assert result.id is not None
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_with_valid_project_reference(self):
        """Creating an entry with a valid project_id returns a LearningEntry."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        mock_db = _mock_db_validate_found()

        async def mock_refresh(obj: LearningEntry) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.timestamp = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = LearningEntryService(db=mock_db, user_id=user_id)
        data = EntryCreate(
            project_id=project_id,
            description="Added authentication module",
        )

        result = await service.create(data)

        assert result.description == "Added authentication module"
        assert result.project_id == project_id
        assert result.skill_id is None
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_create_with_optional_metadata(self):
        """Creating an entry with metadata stores it as entry_metadata."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        mock_db = _mock_db_validate_found()

        async def mock_refresh(obj: LearningEntry) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.timestamp = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = LearningEntryService(db=mock_db, user_id=user_id)
        metadata = {"source": "Udemy", "duration_hours": 2}
        data = EntryCreate(
            skill_id=skill_id,
            description="Watched course",
            metadata=metadata,
        )

        result = await service.create(data)

        assert result.entry_metadata == {"source": "Udemy", "duration_hours": 2}

    @pytest.mark.asyncio
    async def test_create_with_nonexistent_skill_raises_error(self):
        """Creating an entry referencing a non-existent skill raises EntryParentNotFoundError."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        mock_db = _mock_db_validate_not_found()

        service = LearningEntryService(db=mock_db, user_id=user_id)
        data = EntryCreate(
            skill_id=skill_id,
            description="Some progress",
        )

        with pytest.raises(EntryParentNotFoundError) as exc_info:
            await service.create(data)

        assert "Skill" in str(exc_info.value)
        assert str(skill_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_with_nonexistent_project_raises_error(self):
        """Creating an entry referencing a non-existent project raises EntryParentNotFoundError."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        mock_db = _mock_db_validate_not_found()

        service = LearningEntryService(db=mock_db, user_id=user_id)
        data = EntryCreate(
            project_id=project_id,
            description="Some progress",
        )

        with pytest.raises(EntryParentNotFoundError) as exc_info:
            await service.create(data)

        assert "Project" in str(exc_info.value)
        assert str(project_id) in str(exc_info.value)


class TestLearningEntryServiceListBySkill:
    """Tests for LearningEntryService.list_by_skill()."""

    @pytest.mark.asyncio
    async def test_list_by_skill_returns_entries_and_count(self):
        """list_by_skill returns a tuple of (entries, total_count)."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        entries = [
            _make_entry(user_id, skill_id=skill_id, description="Entry 1"),
            _make_entry(user_id, skill_id=skill_id, description="Entry 2"),
        ]

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                # Validation query: skill exists
                mock_result.scalar_one_or_none.return_value = skill_id
            elif call_count == 2:
                # Count query
                mock_result.scalar_one.return_value = 2
            else:
                # Entries query
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = entries
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db = AsyncMock()
        mock_db.execute.side_effect = side_effect

        service = LearningEntryService(db=mock_db, user_id=user_id)
        result_entries, total = await service.list_by_skill(skill_id)

        assert len(result_entries) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_by_skill_nonexistent_raises_error(self):
        """list_by_skill with a non-existent skill raises EntryParentNotFoundError."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        mock_db = _mock_db_validate_not_found()

        service = LearningEntryService(db=mock_db, user_id=user_id)

        with pytest.raises(EntryParentNotFoundError) as exc_info:
            await service.list_by_skill(skill_id)

        assert "Skill" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_by_skill_pagination(self):
        """list_by_skill respects page and size parameters."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        # Simulate page 2 with size 5 from a total of 12 entries
        page_entries = [
            _make_entry(user_id, skill_id=skill_id, description=f"Entry {i}")
            for i in range(5)
        ]

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = skill_id
            elif call_count == 2:
                mock_result.scalar_one.return_value = 12
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = page_entries
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db = AsyncMock()
        mock_db.execute.side_effect = side_effect

        service = LearningEntryService(db=mock_db, user_id=user_id)
        result_entries, total = await service.list_by_skill(skill_id, page=2, size=5)

        assert len(result_entries) == 5
        assert total == 12


class TestLearningEntryServiceListByProject:
    """Tests for LearningEntryService.list_by_project()."""

    @pytest.mark.asyncio
    async def test_list_by_project_returns_entries_and_count(self):
        """list_by_project returns a tuple of (entries, total_count)."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        entries = [
            _make_entry(user_id, project_id=project_id, description="Entry 1"),
            _make_entry(user_id, project_id=project_id, description="Entry 2"),
            _make_entry(user_id, project_id=project_id, description="Entry 3"),
        ]

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = project_id
            elif call_count == 2:
                mock_result.scalar_one.return_value = 3
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = entries
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db = AsyncMock()
        mock_db.execute.side_effect = side_effect

        service = LearningEntryService(db=mock_db, user_id=user_id)
        result_entries, total = await service.list_by_project(project_id)

        assert len(result_entries) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_list_by_project_nonexistent_raises_error(self):
        """list_by_project with a non-existent project raises EntryParentNotFoundError."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        mock_db = _mock_db_validate_not_found()

        service = LearningEntryService(db=mock_db, user_id=user_id)

        with pytest.raises(EntryParentNotFoundError) as exc_info:
            await service.list_by_project(project_id)

        assert "Project" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_by_project_empty_returns_zero(self):
        """list_by_project with no entries returns empty list and zero count."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = project_id
            elif call_count == 2:
                mock_result.scalar_one.return_value = 0
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = []
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db = AsyncMock()
        mock_db.execute.side_effect = side_effect

        service = LearningEntryService(db=mock_db, user_id=user_id)
        result_entries, total = await service.list_by_project(project_id)

        assert result_entries == []
        assert total == 0
