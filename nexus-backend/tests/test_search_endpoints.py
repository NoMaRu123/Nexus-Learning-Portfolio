"""Tests for app.api.search module.

Validates the search endpoint using mocked database sessions and services.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.search import SearchResponse, search
from app.models.project import ProjectRecord
from app.models.skill import SkillRecord
from app.models.user import UserAccount
from app.schemas.project import ProjectResponse
from app.schemas.skill import SkillResponse


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
) -> SkillRecord:
    """Factory for creating SkillRecord instances for testing."""
    return SkillRecord(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        category=category,
        proficiency_level=proficiency_level,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_project_record(
    user_id: uuid.UUID,
    name: str = "My Project",
    description: str | None = "A test project",
    status: str = "in_progress",
    technology_tags: list[str] | None = None,
) -> ProjectRecord:
    """Factory for creating ProjectRecord instances for testing."""
    return ProjectRecord(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        description=description,
        status=status,
        technology_tags=technology_tags or [],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _mock_db_for_search(skills: list[SkillRecord], projects: list[ProjectRecord]) -> AsyncMock:
    """Create a mock db session that returns skills on first execute, projects on second."""
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_scalars = MagicMock()
        mock_result = MagicMock()
        if call_count == 1:
            mock_scalars.all.return_value = skills
        else:
            mock_scalars.all.return_value = projects
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_db = AsyncMock()
    mock_db.execute.side_effect = side_effect
    return mock_db


class TestSearchEndpoint:
    """GET /api/search endpoint tests."""

    @pytest.mark.asyncio
    async def test_search_returns_skills_and_projects(self):
        """Search returns an ApiResponse wrapping a SearchResponse with skills and projects."""
        user = _make_user()
        skills = [_make_skill_record(user.id, name="Python")]
        projects = [_make_project_record(user.id, name="Portfolio")]
        mock_db = _mock_db_for_search(skills, projects)

        response = await search(q="p", category=None, current_user=user, db=mock_db)

        assert isinstance(response.data, SearchResponse)
        assert len(response.data.skills) == 1
        assert len(response.data.projects) == 1
        assert isinstance(response.data.skills[0], SkillResponse)
        assert isinstance(response.data.projects[0], ProjectResponse)
        assert response.data.skills[0].name == "Python"
        assert response.data.projects[0].name == "Portfolio"

    @pytest.mark.asyncio
    async def test_search_with_no_results_returns_empty_lists(self):
        """Search with no matches returns empty skills and projects lists."""
        user = _make_user()
        mock_db = _mock_db_for_search([], [])

        response = await search(q="nonexistent", category=None, current_user=user, db=mock_db)

        assert response.data.skills == []
        assert response.data.projects == []

    @pytest.mark.asyncio
    async def test_search_with_no_params_returns_all(self):
        """Search with no query or category returns all skills and projects."""
        user = _make_user()
        skills = [
            _make_skill_record(user.id, name="Python"),
            _make_skill_record(user.id, name="JavaScript"),
        ]
        projects = [_make_project_record(user.id, name="Portfolio")]
        mock_db = _mock_db_for_search(skills, projects)

        response = await search(q=None, category=None, current_user=user, db=mock_db)

        assert len(response.data.skills) == 2
        assert len(response.data.projects) == 1

    @pytest.mark.asyncio
    async def test_search_with_category_only(self):
        """Search with only a category filter returns filtered skills."""
        user = _make_user()
        skills = [_make_skill_record(user.id, name="Python", category="Programming")]
        projects = [_make_project_record(user.id, name="Portfolio")]
        mock_db = _mock_db_for_search(skills, projects)

        response = await search(q=None, category="Programming", current_user=user, db=mock_db)

        assert len(response.data.skills) == 1
        assert response.data.skills[0].category == "Programming"
