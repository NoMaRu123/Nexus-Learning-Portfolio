"""Learning entry API endpoints.

Provides routes for creating and listing learning entries
linked to skills or projects for the authenticated user.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import UserAccount
from app.schemas.common import ApiErrorResponse, ApiResponse, PaginatedResponse
from app.schemas.entry import EntryCreate, LearningEntryResponse
from app.services.entry import LearningEntryService
from app.services.exceptions import EntryParentNotFoundError

router = APIRouter(prefix="/api/entries", tags=["entries"])


@router.get(
    "",
    response_model=PaginatedResponse[LearningEntryResponse],
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ApiErrorResponse},
        422: {"model": ApiErrorResponse},
    },
)
async def list_entries(
    skill_id: uuid.UUID | None = Query(default=None),
    project_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[LearningEntryResponse]:
    """List learning entries for a skill or project with pagination.

    Exactly one of skill_id or project_id must be provided.

    Raises:
        HTTPException 422: If neither or both skill_id and project_id are provided.
        HTTPException 404: If the referenced skill or project does not exist.
    """
    has_skill = skill_id is not None
    has_project = project_id is not None

    if has_skill == has_project:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Exactly one of skill_id or project_id must be provided",
        )

    service = LearningEntryService(db, current_user.id)

    try:
        if skill_id is not None:
            entries, total = await service.list_by_skill(skill_id, page=page, size=size)
        else:
            entries, total = await service.list_by_project(
                project_id,  # type: ignore[arg-type]
                page=page,
                size=size,
            )
    except EntryParentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    items = [LearningEntryResponse.model_validate(e) for e in entries]
    return PaginatedResponse.create(items=items, total=total, page=page, size=size)


@router.post(
    "",
    response_model=ApiResponse[LearningEntryResponse],
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ApiErrorResponse}},
)
async def create_entry(
    data: EntryCreate,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LearningEntryResponse]:
    """Create a new learning entry linked to a skill or project.

    Raises:
        HTTPException 404: If the referenced skill or project does not exist.
    """
    service = LearningEntryService(db, current_user.id)
    try:
        entry = await service.create(data)
    except EntryParentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    return ApiResponse(data=LearningEntryResponse.model_validate(entry))
