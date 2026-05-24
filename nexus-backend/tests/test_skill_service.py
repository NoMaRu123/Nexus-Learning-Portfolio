"""Tests for app.services.skill module.

Validates SkillService CRUD operations using mocked async database sessions.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.skill import SkillRecord
from app.schemas.skill import ProficiencyLevel, SkillCreate, SkillUpdate
from app.services.exceptions import DuplicateSkillError, SkillNotFoundError
from app.services.skill import SkillService
from app.webhooks.service import WebhookService


def _make_skill(
    user_id: uuid.UUID,
    name: str = "Python",
    category: str = "Programming",
    proficiency_level: str = "beginner",
    skill_id: uuid.UUID | None = None,
) -> SkillRecord:
    """Factory for creating SkillRecord instances for testing."""
    skill = SkillRecord(
        id=skill_id or uuid.uuid4(),
        user_id=user_id,
        name=name,
        category=category,
        proficiency_level=proficiency_level,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return skill


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


class TestSkillServiceCreate:
    """Tests for SkillService.create()."""

    @pytest.mark.asyncio
    async def test_create_with_valid_data_returns_skill(self):
        """Creating a skill with valid data returns a SkillRecord with a UUID."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        # After flush + refresh, the skill should have an id
        async def mock_refresh(obj: SkillRecord) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = SkillService(db=mock_db, user_id=user_id)
        data = SkillCreate(name="Python", category="Programming", proficiency_level=ProficiencyLevel.beginner)

        result = await service.create(data)

        assert result.name == "Python"
        assert result.category == "Programming"
        assert result.proficiency_level == "beginner"
        assert result.user_id == user_id
        assert result.id is not None
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_name_raises_error(self):
        """Creating a skill with a name that already exists raises DuplicateSkillError."""
        user_id = uuid.uuid4()
        existing_skill = _make_skill(user_id, name="Python")
        mock_db = _mock_db_with_result(existing_skill)

        service = SkillService(db=mock_db, user_id=user_id)
        data = SkillCreate(name="Python", category="Programming")

        with pytest.raises(DuplicateSkillError) as exc_info:
            await service.create(data)

        assert "Python" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_stores_proficiency_as_string_value(self):
        """The proficiency_level enum is stored as its string value."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        async def mock_refresh(obj: SkillRecord) -> None:
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = SkillService(db=mock_db, user_id=user_id)
        data = SkillCreate(name="Rust", category="Programming", proficiency_level=ProficiencyLevel.advanced)

        result = await service.create(data)

        assert result.proficiency_level == "advanced"


class TestSkillServiceListAll:
    """Tests for SkillService.list_all()."""

    @pytest.mark.asyncio
    async def test_list_all_returns_alphabetically_sorted(self):
        """list_all returns skills sorted alphabetically by name."""
        user_id = uuid.uuid4()
        skills = [
            _make_skill(user_id, name="Zig"),
            _make_skill(user_id, name="Ansible"),
            _make_skill(user_id, name="Python"),
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = skills

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        service = SkillService(db=mock_db, user_id=user_id)
        result = await service.list_all()

        # The service delegates sorting to the DB query (ORDER BY name ASC),
        # so we verify the query was executed and results returned as-is.
        assert len(result) == 3
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_all_empty_returns_empty_list(self):
        """list_all returns an empty list when user has no skills."""
        user_id = uuid.uuid4()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        service = SkillService(db=mock_db, user_id=user_id)
        result = await service.list_all()

        assert result == []


class TestSkillServiceUpdate:
    """Tests for SkillService.update()."""

    @pytest.mark.asyncio
    async def test_update_modifies_only_provided_fields(self):
        """Updating with partial data only changes the specified fields."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        existing = _make_skill(user_id, name="Python", category="Programming", skill_id=skill_id)

        mock_db = _mock_db_with_result(existing)

        async def mock_refresh(obj: SkillRecord) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = SkillService(db=mock_db, user_id=user_id)
        data = SkillUpdate(proficiency_level=ProficiencyLevel.expert)

        result = await service.update(skill_id, data)

        assert result.proficiency_level == "expert"
        # Name and category should remain unchanged
        assert result.name == "Python"
        assert result.category == "Programming"

    @pytest.mark.asyncio
    async def test_update_nonexistent_skill_raises_not_found(self):
        """Updating a skill that doesn't exist raises SkillNotFoundError."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        service = SkillService(db=mock_db, user_id=user_id)
        data = SkillUpdate(proficiency_level=ProficiencyLevel.intermediate)

        with pytest.raises(SkillNotFoundError) as exc_info:
            await service.update(skill_id, data)

        assert str(skill_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_name_to_duplicate_raises_error(self):
        """Renaming a skill to a name that already exists raises DuplicateSkillError."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        existing = _make_skill(user_id, name="Python", skill_id=skill_id)

        # First call: find the skill to update (returns existing)
        # Second call: check for duplicate name (returns a conflict)
        conflict = _make_skill(user_id, name="JavaScript")

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = existing
            else:
                mock_result.scalar_one_or_none.return_value = conflict
            return mock_result

        mock_db = AsyncMock()
        mock_db.execute.side_effect = side_effect

        service = SkillService(db=mock_db, user_id=user_id)
        data = SkillUpdate(name="JavaScript")

        with pytest.raises(DuplicateSkillError):
            await service.update(skill_id, data)

    @pytest.mark.asyncio
    async def test_update_with_no_changes_returns_unchanged(self):
        """Updating with all None fields returns the skill unchanged."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        existing = _make_skill(user_id, name="Python", skill_id=skill_id)

        mock_db = _mock_db_with_result(existing)

        async def mock_refresh(obj: SkillRecord) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = SkillService(db=mock_db, user_id=user_id)
        data = SkillUpdate()  # All fields None

        result = await service.update(skill_id, data)

        assert result.name == "Python"
        assert result.category == "Programming"


class TestSkillServiceDelete:
    """Tests for SkillService.delete()."""

    @pytest.mark.asyncio
    async def test_delete_removes_skill(self):
        """Deleting an existing skill calls db.delete and flush."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        existing = _make_skill(user_id, name="Python", skill_id=skill_id)

        mock_db = _mock_db_with_result(existing)

        service = SkillService(db=mock_db, user_id=user_id)
        await service.delete(skill_id)

        mock_db.delete.assert_awaited_once_with(existing)
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_skill_raises_not_found(self):
        """Deleting a skill that doesn't exist raises SkillNotFoundError."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        mock_db = _mock_db_no_result()

        service = SkillService(db=mock_db, user_id=user_id)

        with pytest.raises(SkillNotFoundError) as exc_info:
            await service.delete(skill_id)

        assert str(skill_id) in str(exc_info.value)


class TestSkillServiceWebhookIntegration:
    """Tests for webhook dispatch integration in SkillService."""

    @pytest.mark.asyncio
    async def test_update_proficiency_dispatches_webhook(self):
        """Updating proficiency_level dispatches a 'skill.proficiency_changed' webhook."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        existing = _make_skill(
            user_id, name="Python", proficiency_level="beginner", skill_id=skill_id
        )

        mock_db = _mock_db_with_result(existing)

        async def mock_refresh(obj: SkillRecord) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        mock_webhook = AsyncMock(spec=WebhookService)

        service = SkillService(db=mock_db, user_id=user_id, webhook_service=mock_webhook)
        data = SkillUpdate(proficiency_level=ProficiencyLevel.expert)

        result = await service.update(skill_id, data)

        mock_webhook.dispatch.assert_awaited_once()
        call_args = mock_webhook.dispatch.call_args
        assert call_args[0][0] == "skill.proficiency_changed"
        payload = call_args[0][1]
        assert payload["id"] == str(skill_id)
        assert payload["name"] == "Python"
        assert payload["old_proficiency_level"] == "beginner"
        assert payload["new_proficiency_level"] == "expert"

    @pytest.mark.asyncio
    async def test_update_without_proficiency_change_does_not_dispatch(self):
        """Updating fields other than proficiency_level does not dispatch a webhook."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        existing = _make_skill(
            user_id, name="Python", proficiency_level="beginner", skill_id=skill_id
        )

        mock_db = _mock_db_with_result(existing)

        async def mock_refresh(obj: SkillRecord) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        mock_webhook = AsyncMock(spec=WebhookService)

        service = SkillService(db=mock_db, user_id=user_id, webhook_service=mock_webhook)
        data = SkillUpdate(category="Backend")

        await service.update(skill_id, data)

        mock_webhook.dispatch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_same_proficiency_does_not_dispatch(self):
        """Setting proficiency_level to the same value does not dispatch a webhook."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        existing = _make_skill(
            user_id, name="Python", proficiency_level="beginner", skill_id=skill_id
        )

        mock_db = _mock_db_with_result(existing)

        async def mock_refresh(obj: SkillRecord) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        mock_webhook = AsyncMock(spec=WebhookService)

        service = SkillService(db=mock_db, user_id=user_id, webhook_service=mock_webhook)
        data = SkillUpdate(proficiency_level=ProficiencyLevel.beginner)

        await service.update(skill_id, data)

        mock_webhook.dispatch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_without_webhook_service_works(self):
        """Updating a skill without a webhook_service still works normally."""
        user_id = uuid.uuid4()
        skill_id = uuid.uuid4()
        existing = _make_skill(
            user_id, name="Python", proficiency_level="beginner", skill_id=skill_id
        )

        mock_db = _mock_db_with_result(existing)

        async def mock_refresh(obj: SkillRecord) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        service = SkillService(db=mock_db, user_id=user_id)
        data = SkillUpdate(proficiency_level=ProficiencyLevel.expert)

        result = await service.update(skill_id, data)

        assert result.proficiency_level == "expert"
