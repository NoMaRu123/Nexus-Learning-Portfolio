"""Project CRUD API endpoints.

Provides routes for creating, listing, updating, and deleting
project records for the authenticated user.
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
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.exceptions import ProjectNotFoundError
from app.services.project import ProjectService
from app.webhooks.service import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get(
    "",
    response_model=ApiResponse[list[ProjectResponse]],
    status_code=status.HTTP_200_OK,
)
async def list_projects(
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ProjectResponse]]:
    """List all projects for the authenticated user, sorted by created_at descending."""
    service = ProjectService(db, current_user.id)
    projects = await service.list_all()
    return ApiResponse(data=[ProjectResponse.model_validate(p) for p in projects])


@router.post(
    "",
    response_model=ApiResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    data: ProjectCreate,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ProjectResponse]:
    """Create a new project for the authenticated user."""
    webhook_service = WebhookService(get_settings())
    service = ProjectService(db, current_user.id, webhook_service=webhook_service)
    project = await service.create(data)
    return ApiResponse(data=ProjectResponse.model_validate(project))


@router.put(
    "/{project_id}",
    response_model=ApiResponse[ProjectResponse],
    status_code=status.HTTP_200_OK,
    responses={404: {"model": ApiErrorResponse}},
)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ProjectResponse]:
    """Update an existing project for the authenticated user.

    Raises:
        HTTPException 404: If the project does not exist.
    """
    service = ProjectService(db, current_user.id)
    try:
        project = await service.update(project_id, data)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    return ApiResponse(data=ProjectResponse.model_validate(project))


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ApiErrorResponse}},
)
async def delete_project(
    project_id: uuid.UUID,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a project for the authenticated user. Cascade deletes learning entries.

    Raises:
        HTTPException 404: If the project does not exist.
    """
    service = ProjectService(db, current_user.id)
    try:
        await service.delete(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
