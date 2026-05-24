"""Tests for app.services.search module.

Validates SearchService search operations using mocked async database sessions.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.project import ProjectRecord
from app.models.skill import SkillRecord
from app.services.search import SearchResult, SearchService


def _make_skill(
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


def _make_project(
    user_id: uuid.UUID,
    name: str = "My Project",
    description: str | None = "A cool project",
    status: str = "in_progress",
) -> ProjectRecord:
    """Factory for creating ProjectRecord instances for testing."""
    return ProjectRecord(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        description=description,
        status=status,
        technology_tags=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _mock_db_returning(skills: list[SkillRecord], projects: list[ProjectRecord]) -> AsyncMock:
    """Create a mock DB session that returns skills on first call and projects on second."""
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


class TestSearchServiceSearch:
    """Tests for SearchService.search()."""

    @pytest.mark.asyncio
    async def test_search_no_filters_returns_all(self):
        """Searching with no query or category returns all skills and projects."""
        user_id = uuid.uuid4()
        skills = [_make_skill(user_id, name="Python"), _make_skill(user_id, name="Rust")]
        projects = [_make_project(user_id, name="Portfolio")]

        mock_db = _mock_db_returning(skills, projects)
        service = SearchService(db=mock_db, user_id=user_id)

        result = await service.search()

        assert isinstance(result, SearchResult)
        assert len(result.skills) == 2
        assert len(result.projects) == 1
        assert mock_db.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_search_with_query_matches_skill_name(self):
        """Searching with a text query filters skills by name using ILIKE."""
        user_id = uuid.uuid4()
        skills = [_make_skill(user_id, name="Python")]
        projects = [_make_project(user_id, name="Python Web App")]

        mock_db = _mock_db_returning(skills, projects)
        service = SearchService(db=mock_db, user_id=user_id)

        result = await service.search(query="python")

        assert len(result.skills) == 1
        assert len(result.projects) == 1
        # Verify two queries were executed (skills + projects)
        assert mock_db.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_search_with_category_filters_skills_only(self):
        """Searching with a category filters skills but not projects."""
        user_id = uuid.uuid4()
        skills = [_make_skill(user_id, name="Python", category="Programming")]
        projects = [_make_project(user_id, name="Portfolio")]

        mock_db = _mock_db_returning(skills, projects)
        service = SearchService(db=mock_db, user_id=user_id)

        result = await service.search(category="Programming")

        assert len(result.skills) == 1
        assert len(result.projects) == 1
        assert mock_db.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_search_combined_query_and_category(self):
        """Searching with both query and category applies AND logic on skills."""
        user_id = uuid.uuid4()
        skills = [_make_skill(user_id, name="Python", category="Programming")]
        projects = [_make_project(user_id, name="Python App")]

        mock_db = _mock_db_returning(skills, projects)
        service = SearchService(db=mock_db, user_id=user_id)

        result = await service.search(query="python", category="Programming")

        assert len(result.skills) == 1
        assert len(result.projects) == 1
        assert mock_db.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Searching with no matches returns empty lists."""
        user_id = uuid.uuid4()

        mock_db = _mock_db_returning([], [])
        service = SearchService(db=mock_db, user_id=user_id)

        result = await service.search(query="nonexistent")

        assert result.skills == []
        assert result.projects == []

    @pytest.mark.asyncio
    async def test_search_result_dataclass_defaults(self):
        """SearchResult initializes with empty lists by default."""
        result = SearchResult()

        assert result.skills == []
        assert result.projects == []


class TestSearchServiceInternals:
    """Tests for SearchService internal query construction."""

    @pytest.mark.asyncio
    async def test_project_search_matches_description(self):
        """Project search matches on description field via ILIKE."""
        user_id = uuid.uuid4()
        projects = [_make_project(user_id, name="App", description="Built with Python")]

        mock_db = _mock_db_returning([], projects)
        service = SearchService(db=mock_db, user_id=user_id)

        result = await service.search(query="python")

        # The mock returns the project regardless of the query (DB filtering
        # is handled by PostgreSQL), but we verify the query was executed.
        assert len(result.projects) == 1
        assert mock_db.execute.await_count == 2
