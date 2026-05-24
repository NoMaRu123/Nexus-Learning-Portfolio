"""User profile management API endpoints.

Provides routes for retrieving, updating, and uploading a profile
picture for the authenticated user.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import UserAccount
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.schemas.profile import ProfileUpdate, PublicProfileResponse, UserProfileResponse
from app.services.exceptions import InvalidMimeTypeError, ProfileNotFoundError
from app.services.profile import ProfileService
from app.storage import get_storage_backend

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get(
    "",
    response_model=ApiResponse[UserProfileResponse],
    status_code=status.HTTP_200_OK,
    responses={404: {"model": ApiErrorResponse}},
)
async def get_profile(
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[UserProfileResponse]:
    """Get the profile for the authenticated user.

    In Tracker Mode, requires authentication.
    Portfolio Mode public access will be handled in task 10.1.
    """
    storage = get_storage_backend(settings)
    service = ProfileService(db, current_user.id, storage)
    try:
        profile = await service.get_profile()
    except ProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    return ApiResponse(data=UserProfileResponse.model_validate(profile))


@router.put(
    "",
    response_model=ApiResponse[UserProfileResponse],
    status_code=status.HTTP_200_OK,
    responses={404: {"model": ApiErrorResponse}},
)
async def update_profile(
    data: ProfileUpdate,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[UserProfileResponse]:
    """Update the profile for the authenticated user.

    Only provided (non-None) fields are updated.
    """
    storage = get_storage_backend(settings)
    service = ProfileService(db, current_user.id, storage)
    try:
        profile = await service.update_profile(data)
    except ProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    return ApiResponse(data=UserProfileResponse.model_validate(profile))


@router.post(
    "/picture",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ApiErrorResponse},
        422: {"model": ApiErrorResponse},
    },
)
async def upload_profile_picture(
    file: UploadFile,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[dict]:
    """Upload a profile picture for the authenticated user.

    Accepts JPEG, PNG, and WebP images. The backend validates the
    MIME type, strips EXIF metadata, generates a UUID-based filename,
    and stores the image via the configured storage backend.

    Returns the new picture URL on success.

    Raises:
        HTTPException 404: If no profile exists for the user.
        HTTPException 422: If the file MIME type is not allowed.
    """
    storage = get_storage_backend(settings)
    service = ProfileService(db, current_user.id, storage)

    file_data = await file.read()
    content_type = file.content_type or ""

    try:
        picture_url = await service.upload_picture(
            file_data=file_data,
            content_type=content_type,
            original_filename=file.filename or "unknown",
        )
    except InvalidMimeTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except ProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return ApiResponse(data={"picture_url": picture_url})
