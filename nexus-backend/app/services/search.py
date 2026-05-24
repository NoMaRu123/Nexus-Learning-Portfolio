"""Search service for skills and projects.

Provides case-insensitive text search across SkillRecords and ProjectRecords
using PostgreSQL ILIKE, with optional category filtering.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectRecord
from app.models.skill import SkillRecord


@dataclass
class SearchResult:
    """Combined search results containing matching skills and projects."""

    skills: list[SkillRecord] = field(default_factory=list)
    projects: list[ProjectRecord] = field(default_factory=list)


class SearchService:
    """Service handling search across skills and projects for a single user.

    Uses PostgreSQL ILIKE for case-insensitive matching on name and
    description fields. Supports query-only, category-only, and
    combined query+category filtering with AND logic.
    """

    def __init__(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        self._db = db
        self._user_id = user_id

    async def search(
        self,
        query: str | None = None,
        category: str | None = None,
    ) -> SearchResult:
        """Search skills and projects by text query and/or category.

        Args:
            query: Optional text to match against name and description
                fields using case-insensitive ILIKE.
            category: Optional category to filter skills by exact
                case-insensitive match.

        Returns:
            A SearchResult containing separate lists of matching
            SkillRecords and ProjectRecords.
        """
        skills = await self._search_skills(query, category)
        projects = await self._search_projects(query)
        return SearchResult(skills=skills, projects=projects)

    async def _search_skills(
        self,
        query: str | None,
        category: str | None,
    ) -> list[SkillRecord]:
        """Search skills with optional text query and category filter.

        When both query and category are provided, results must match
        both criteria (AND logic).
        """
        stmt = select(SkillRecord).where(
            SkillRecord.user_id == self._user_id
        )

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(SkillRecord.name.ilike(pattern))

        if category:
            stmt = stmt.where(SkillRecord.category.ilike(category))

        stmt = stmt.order_by(SkillRecord.name.asc())
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def _search_projects(
        self,
        query: str | None,
    ) -> list[ProjectRecord]:
        """Search projects with optional text query on name and description.

        Projects do not have a category field, so category filtering
        is not applied.
        """
        stmt = select(ProjectRecord).where(
            ProjectRecord.user_id == self._user_id
        )

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    ProjectRecord.name.ilike(pattern),
                    ProjectRecord.description.ilike(pattern),
                )
            )

        stmt = stmt.order_by(ProjectRecord.name.asc())
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
