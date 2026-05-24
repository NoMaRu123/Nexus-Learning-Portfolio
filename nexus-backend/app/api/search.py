"""Search API endpoint.

Provides a route for searching skills and projects by text query
and/or category filter for the authenticated user.
"""

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import UserAccount
from app.schemas.common import ApiResponse
from app.schemas.project import ProjectResponse
from app.schemas.skill import SkillResponse
from app.services.search import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchResponse(BaseModel):
    """Combined search results containing matching skills and projects."""

    skills: list[SkillResponse]
    projects: list[ProjectResponse]


@router.get(
    "",
    response_model=ApiResponse[SearchResponse],
    status_code=status.HTTP_200_OK,
)
async def search(
    q: str | None = Query(default=None, description="Text to search in name and description fields"),
    category: str | None = Query(default=None, description="Category to filter skills by"),
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SearchResponse]:
    """Search skills and projects by text query and/or category.

    Returns matching skills and projects for the authenticated user.
    When both query and category are provided, results must match
    both criteria (AND logic).
    """
    service = SearchService(db, current_user.id)
    result = await service.search(query=q, category=category)
    return ApiResponse(
        data=SearchResponse(
            skills=[SkillResponse.model_validate(s) for s in result.skills],
            projects=[ProjectResponse.model_validate(p) for p in result.projects],
        )
    )
