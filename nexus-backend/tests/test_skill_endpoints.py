"""Tests for app.api.skills module.

Validates skill CRUD endpoints using mocked database sessions and services.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.skills import create_skill, delete_skill, list_skills, update_skill
from app.models.skill import SkillRecord
from app.models.user import UserAccount
from app.schemas.skill import ProficiencyLevel, SkillCreate, SkillResponse, SkillUpdate
from app.services.exceptions import DuplicateSkillError, SkillNotFoundError


def _make_user(user_id: uuid.UUID | None = None) -> UserAccount:
    """Factory for creating a mock UserAccount."""
    user = MagicMock(spec=UserAccount)
    user.id = user_id or uuid.uuid4()
    user.email = "test@example.com"
    return user


def _make_skill_record(
    user_id: uuid.UUID,
    name: str = "Python",
    category: str = "Programming",
    proficiency_level: str = "beginner",
    skill_id: uuid.UUID | None = None,
) -> SkillRecord:
    """Factory for creating SkillRecord instances for testing."""
    return SkillRecord(
        id=skill_id or uuid.uuid4(),
        user_id=user_id,
        name=name,
        category=category,
        proficiency_level=proficiency_level,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestListSkills:
    """GET /api/skills endpoint tests."""

    @pytest.mark.asyncio
    async def test_list_skills_returns_wrapped_response(self):
        """Listing skills returns an ApiResponse wrapping a list of SkillResponse."""
        user = _make_user()
        skills = [
            _make_skill_record(user.id, name="Ansible"),
            _make_skill_record(user.id, name="Python"),
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = skills

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        response = await list_skills(current_user=user, db=mock_db)

        assert len(response.data) == 2
        assert all(isinstance(s, SkillResponse) for s in response.data)
        assert response.data[0].name == "Ansible"
        assert response.data[1].name == "Python"

    @pytest.mark.asyncio
    async def test_list_skills_empty_returns_empty_list(self):
        """Listing skills when user has none returns an empty data list."""
        user = _make_user()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        response = await list_skills(current_user=user, db=mock_db)

        assert response.data == []


class TestCreateSkill:
    """POST /api/skills endpoint tests."""

    @pytest.mark.asyncio
    async def test_create_skill_returns_wrapped_response(self):
        """Creating a skill returns an ApiResponse wrapping a SkillResponse."""
        user = _make_user()
        data = SkillCreate(name="Python", category="Programming", proficiency_level=ProficiencyLevel.beginner)

        # Mock DB: no duplicate found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()

        async def mock_refresh(obj: SkillRecord) -> None:
            if not obj.id:
                obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        response = await create_skill(data=data, current_user=user, db=mock_db)

        assert isinstance(response.data, SkillResponse)
        assert response.data.name == "Python"
        assert response.data.category == "Programming"

    @pytest.mark.asyncio
    async def test_create_duplicate_skill_returns_409(self):
        """Creating a skill with a duplicate name raises 409 Conflict."""
        user = _make_user()
        existing = _make_skill_record(user.id, name="Python")
        data = SkillCreate(name="Python", category="Programming")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await create_skill(data=data, current_user=user, db=mock_db)

        assert exc_info.value.status_code == 409
        assert "Python" in exc_info.value.detail


class TestUpdateSkill:
    """PUT /api/skills/{id} endpoint tests."""

    @pytest.mark.asyncio
    async def test_update_skill_returns_wrapped_response(self):
        """Updating a skill returns an ApiResponse wrapping the updated SkillResponse."""
        user = _make_user()
        skill_id = uuid.uuid4()
        existing = _make_skill_record(user.id, name="Python", skill_id=skill_id)
        data = SkillUpdate(proficiency_level=ProficiencyLevel.expert)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj: SkillRecord) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        response = await update_skill(skill_id=skill_id, data=data, current_user=user, db=mock_db)

        assert isinstance(response.data, SkillResponse)
        assert response.data.proficiency_level == "expert"

    @pytest.mark.asyncio
    async def test_update_nonexistent_skill_returns_404(self):
        """Updating a skill that doesn't exist raises 404 Not Found."""
        user = _make_user()
        skill_id = uuid.uuid4()
        data = SkillUpdate(proficiency_level=ProficiencyLevel.intermediate)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await update_skill(skill_id=skill_id, data=data, current_user=user, db=mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_duplicate_name_returns_409(self):
        """Renaming a skill to a duplicate name raises 409 Conflict."""
        user = _make_user()
        skill_id = uuid.uuid4()
        existing = _make_skill_record(user.id, name="Python", skill_id=skill_id)
        conflict = _make_skill_record(user.id, name="JavaScript")
        data = SkillUpdate(name="JavaScript")

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

        with pytest.raises(HTTPException) as exc_info:
            await update_skill(skill_id=skill_id, data=data, current_user=user, db=mock_db)

        assert exc_info.value.status_code == 409


class TestDeleteSkill:
    """DELETE /api/skills/{id} endpoint tests."""

    @pytest.mark.asyncio
    async def test_delete_skill_returns_204(self):
        """Deleting an existing skill returns a 204 No Content response."""
        user = _make_user()
        skill_id = uuid.uuid4()
        existing = _make_skill_record(user.id, name="Python", skill_id=skill_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        response = await delete_skill(skill_id=skill_id, current_user=user, db=mock_db)

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_nonexistent_skill_returns_404(self):
        """Deleting a skill that doesn't exist raises 404 Not Found."""
        user = _make_user()
        skill_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await delete_skill(skill_id=skill_id, current_user=user, db=mock_db)

        assert exc_info.value.status_code == 404
