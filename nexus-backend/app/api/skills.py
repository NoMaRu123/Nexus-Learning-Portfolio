"""Skill CRUD API endpoints.

Provides routes for creating, listing, updating, and deleting
skill records for the authenticated user.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import UserAccount
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.schemas.skill import SkillCreate, SkillResponse, SkillUpdate
from app.services.exceptions import DuplicateSkillError, SkillNotFoundError
from app.services.skill import SkillService
from app.webhooks.service import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get(
    "",
    response_model=ApiResponse[list[SkillResponse]],
    status_code=status.HTTP_200_OK,
)
async def list_skills(
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SkillResponse]]:
    """List all skills for the authenticated user, sorted alphabetically by name."""
    service = SkillService(db, current_user.id)
    skills = await service.list_all()
    return ApiResponse(data=[SkillResponse.model_validate(s) for s in skills])


@router.post(
    "",
    response_model=ApiResponse[SkillResponse],
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ApiErrorResponse}},
)
async def create_skill(
    data: SkillCreate,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SkillResponse]:
    """Create a new skill for the authenticated user.

    Raises:
        HTTPException 409: If a skill with the same name already exists.
    """
    service = SkillService(db, current_user.id)
    try:
        skill = await service.create(data)
    except DuplicateSkillError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return ApiResponse(data=SkillResponse.model_validate(skill))


@router.put(
    "/{skill_id}",
    response_model=ApiResponse[SkillResponse],
    status_code=status.HTTP_200_OK,
    responses={404: {"model": ApiErrorResponse}, 409: {"model": ApiErrorResponse}},
)
async def update_skill(
    skill_id: uuid.UUID,
    data: SkillUpdate,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SkillResponse]:
    """Update an existing skill for the authenticated user.

    Raises:
        HTTPException 404: If the skill does not exist.
        HTTPException 409: If the new name conflicts with another skill.
    """
    webhook_service = WebhookService(get_settings())
    service = SkillService(db, current_user.id, webhook_service=webhook_service)
    try:
        skill = await service.update(skill_id, data)
    except SkillNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except DuplicateSkillError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return ApiResponse(data=SkillResponse.model_validate(skill))


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ApiErrorResponse}},
)
async def delete_skill(
    skill_id: uuid.UUID,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a skill for the authenticated user. Cascade deletes learning entries.

    Raises:
        HTTPException 404: If the skill does not exist.
    """
    service = SkillService(db, current_user.id)
    try:
        await service.delete(skill_id)
    except SkillNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
