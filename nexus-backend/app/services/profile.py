"""Profile management service.

Encapsulates business logic for retrieving, updating, and managing
user profiles including profile picture uploads with EXIF stripping.
"""

import io
import uuid

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import UserProfile
from app.schemas.profile import ProfileUpdate
from app.services.exceptions import InvalidMimeTypeError, ProfileNotFoundError
from app.storage.base import StorageBackend

ALLOWED_MIME_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}

MIME_TO_EXTENSION: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MIME_TO_PIL_FORMAT: dict[str, str] = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


class ProfileService:
    """Service handling profile operations for a single user."""

    def __init__(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        storage: StorageBackend,
    ) -> None:
        self._db = db
        self._user_id = user_id
        self._storage = storage

    async def get_profile(self) -> UserProfile:
        """Return the full UserProfile for the authenticated user.

        Returns:
            The UserProfile record.

        Raises:
            ProfileNotFoundError: If no profile exists for this user.
        """
        return await self._get_profile_or_raise()

    async def update_profile(self, data: ProfileUpdate) -> UserProfile:
        """Update the user profile with only the provided (non-None) fields.

        Contact email format validation is handled by the Pydantic schema
        (EmailStr type on ProfileUpdate.contact_email).

        Args:
            data: Validated profile update payload with optional fields.

        Returns:
            The updated UserProfile record.

        Raises:
            ProfileNotFoundError: If no profile exists for this user.
        """
        profile = await self._get_profile_or_raise()

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in update_data.items():
            setattr(profile, field, value)

        await self._db.flush()
        await self._db.refresh(profile)
        return profile

    async def upload_picture(
        self,
        file_data: bytes,
        content_type: str,
        original_filename: str,
    ) -> str:
        """Upload a profile picture after validation and EXIF stripping.

        Steps:
        1. Validate MIME type against allowlist
        2. Strip EXIF metadata using Pillow
        3. Generate UUID-based filename with correct extension
        4. Store via StorageBackend
        5. Delete previous picture if one exists
        6. Update profile picture_url

        Args:
            file_data: Raw image bytes.
            content_type: MIME type of the uploaded file.
            original_filename: Original filename (used only for logging context).

        Returns:
            The public URL of the newly stored picture.

        Raises:
            InvalidMimeTypeError: If content_type is not in the allowlist.
            ProfileNotFoundError: If no profile exists for this user.
        """
        if content_type not in ALLOWED_MIME_TYPES:
            raise InvalidMimeTypeError(content_type)

        profile = await self._get_profile_or_raise()

        cleaned_data = self._strip_exif(file_data, content_type)

        extension = MIME_TO_EXTENSION[content_type]
        new_filename = f"{uuid.uuid4()}{extension}"

        new_url = await self._storage.save(new_filename, cleaned_data, content_type)

        if profile.picture_url:
            old_filename = self._extract_filename(profile.picture_url)
            if old_filename:
                await self._storage.delete(old_filename)

        profile.picture_url = new_url
        await self._db.flush()
        await self._db.refresh(profile)

        return new_url

    async def get_public_profile(self) -> UserProfile:
        """Return profile data for public display.

        Returns the same UserProfile object as get_profile(). The API
        layer uses PublicProfileResponse to exclude private fields
        during serialization.

        Returns:
            The UserProfile record.

        Raises:
            ProfileNotFoundError: If no profile exists for this user.
        """
        return await self._get_profile_or_raise()

    async def _get_profile_or_raise(self) -> UserProfile:
        """Fetch the profile by user_id, or raise ProfileNotFoundError."""
        result = await self._db.execute(
            select(UserProfile).where(UserProfile.user_id == self._user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise ProfileNotFoundError(str(self._user_id))
        return profile

    @staticmethod
    def _strip_exif(file_data: bytes, content_type: str) -> bytes:
        """Remove EXIF metadata from image data using Pillow.

        Opens the image, extracts pixel data, and re-saves without
        any metadata attached.

        Args:
            file_data: Raw image bytes potentially containing EXIF data.
            content_type: MIME type used to determine the output format.

        Returns:
            Clean image bytes with EXIF metadata stripped.
        """
        image = Image.open(io.BytesIO(file_data))
        output = io.BytesIO()
        pil_format = MIME_TO_PIL_FORMAT[content_type]
        image.save(output, format=pil_format)
        return output.getvalue()

    @staticmethod
    def _extract_filename(url: str) -> str | None:
        """Extract the filename from a storage URL.

        Handles URLs in the form ``/uploads/filename.ext`` or
        ``https://host/path/filename.ext``.

        Args:
            url: The full or relative URL of the stored file.

        Returns:
            The filename portion, or None if extraction fails.
        """
        if not url:
            return None
        # Take the last path segment as the filename
        return url.rstrip("/").rsplit("/", 1)[-1] or None
