"""Tests for app.api.profile module.

Validates profile management endpoints using mocked database sessions
and storage backends.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from app.api.profile import get_profile, update_profile, upload_profile_picture
from app.core.config import Settings
from app.models.profile import UserProfile
from app.models.user import UserAccount
from app.schemas.profile import ProfileUpdate, UserProfileResponse


def _make_user(user_id: uuid.UUID | None = None) -> UserAccount:
    """Factory for creating a mock UserAccount."""
    user = MagicMock(spec=UserAccount)
    user.id = user_id or uuid.uuid4()
    user.email = "test@example.com"
    return user


def _make_profile(
    user_id: uuid.UUID,
    name: str | None = "Test User",
    bio: str | None = "A test bio",
    contact_email: str | None = "contact@example.com",
    social_links: dict | None = None,
    picture_url: str | None = None,
    profile_id: uuid.UUID | None = None,
) -> UserProfile:
    """Factory for creating UserProfile instances for testing."""
    return UserProfile(
        id=profile_id or uuid.uuid4(),
        user_id=user_id,
        name=name,
        bio=bio,
        contact_email=contact_email,
        social_links=social_links or {},
        picture_url=picture_url,
        updated_at=datetime.now(timezone.utc),
    )


def _make_settings() -> MagicMock:
    """Factory for creating a mock Settings instance."""
    settings = MagicMock(spec=Settings)
    settings.storage_backend = "local"
    settings.storage_local_path = "./uploads"
    return settings


class TestGetProfile:
    """GET /api/profile endpoint tests."""

    @pytest.mark.asyncio
    async def test_get_profile_returns_wrapped_response(self):
        """Getting a profile returns an ApiResponse wrapping a UserProfileResponse."""
        user = _make_user()
        profile = _make_profile(user.id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        settings = _make_settings()

        with patch("app.api.profile.get_storage_backend") as mock_storage_factory:
            mock_storage_factory.return_value = MagicMock()
            response = await get_profile(
                current_user=user, db=mock_db, settings=settings
            )

        assert isinstance(response.data, UserProfileResponse)
        assert response.data.name == "Test User"
        assert response.data.bio == "A test bio"
        assert response.data.contact_email == "contact@example.com"

    @pytest.mark.asyncio
    async def test_get_profile_not_found_returns_404(self):
        """Getting a profile that doesn't exist raises 404 Not Found."""
        user = _make_user()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        settings = _make_settings()

        with patch("app.api.profile.get_storage_backend") as mock_storage_factory:
            mock_storage_factory.return_value = MagicMock()
            with pytest.raises(HTTPException) as exc_info:
                await get_profile(
                    current_user=user, db=mock_db, settings=settings
                )

        assert exc_info.value.status_code == 404


class TestUpdateProfile:
    """PUT /api/profile endpoint tests."""

    @pytest.mark.asyncio
    async def test_update_profile_returns_wrapped_response(self):
        """Updating a profile returns an ApiResponse wrapping the updated UserProfileResponse."""
        user = _make_user()
        profile = _make_profile(user.id)
        data = ProfileUpdate(name="Updated Name", bio="Updated bio")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        settings = _make_settings()

        with patch("app.api.profile.get_storage_backend") as mock_storage_factory:
            mock_storage_factory.return_value = MagicMock()
            response = await update_profile(
                data=data, current_user=user, db=mock_db, settings=settings
            )

        assert isinstance(response.data, UserProfileResponse)
        assert response.data.name == "Updated Name"
        assert response.data.bio == "Updated bio"

    @pytest.mark.asyncio
    async def test_update_profile_not_found_returns_404(self):
        """Updating a profile that doesn't exist raises 404 Not Found."""
        user = _make_user()
        data = ProfileUpdate(name="Updated Name")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        settings = _make_settings()

        with patch("app.api.profile.get_storage_backend") as mock_storage_factory:
            mock_storage_factory.return_value = MagicMock()
            with pytest.raises(HTTPException) as exc_info:
                await update_profile(
                    data=data, current_user=user, db=mock_db, settings=settings
                )

        assert exc_info.value.status_code == 404


class TestUploadProfilePicture:
    """POST /api/profile/picture endpoint tests."""

    @pytest.mark.asyncio
    async def test_upload_picture_returns_picture_url(self):
        """Uploading a valid picture returns an ApiResponse with the new picture URL."""
        user = _make_user()
        profile = _make_profile(user.id)
        expected_url = "/uploads/new-picture.jpg"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh

        mock_storage = AsyncMock()
        mock_storage.save.return_value = expected_url

        settings = _make_settings()

        mock_file = AsyncMock(spec=UploadFile)
        mock_file.read.return_value = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        mock_file.content_type = "image/jpeg"
        mock_file.filename = "photo.jpg"

        with (
            patch("app.api.profile.get_storage_backend") as mock_storage_factory,
            patch("app.services.profile.ProfileService.upload_picture") as mock_upload,
        ):
            mock_storage_factory.return_value = mock_storage
            mock_upload.return_value = expected_url

            response = await upload_profile_picture(
                file=mock_file, current_user=user, db=mock_db, settings=settings
            )

        assert response.data["picture_url"] == expected_url

    @pytest.mark.asyncio
    async def test_upload_picture_invalid_mime_returns_422(self):
        """Uploading a file with an invalid MIME type raises 422."""
        user = _make_user()
        profile = _make_profile(user.id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        mock_storage = AsyncMock()
        settings = _make_settings()

        mock_file = AsyncMock(spec=UploadFile)
        mock_file.read.return_value = b"not an image"
        mock_file.content_type = "application/pdf"
        mock_file.filename = "document.pdf"

        with patch("app.api.profile.get_storage_backend") as mock_storage_factory:
            mock_storage_factory.return_value = mock_storage
            with pytest.raises(HTTPException) as exc_info:
                await upload_profile_picture(
                    file=mock_file, current_user=user, db=mock_db, settings=settings
                )

        assert exc_info.value.status_code == 422
        assert "application/pdf" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_picture_profile_not_found_returns_404(self):
        """Uploading a picture when no profile exists raises 404."""
        user = _make_user()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        mock_storage = AsyncMock()
        settings = _make_settings()

        mock_file = AsyncMock(spec=UploadFile)
        mock_file.read.return_value = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        mock_file.content_type = "image/jpeg"
        mock_file.filename = "photo.jpg"

        with patch("app.api.profile.get_storage_backend") as mock_storage_factory:
            mock_storage_factory.return_value = mock_storage
            with pytest.raises(HTTPException) as exc_info:
                await upload_profile_picture(
                    file=mock_file, current_user=user, db=mock_db, settings=settings
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_picture_empty_content_type_returns_422(self):
        """Uploading a file with no content type raises 422."""
        user = _make_user()
        profile = _make_profile(user.id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        mock_storage = AsyncMock()
        settings = _make_settings()

        mock_file = AsyncMock(spec=UploadFile)
        mock_file.read.return_value = b"some data"
        mock_file.content_type = None
        mock_file.filename = "photo.jpg"

        with patch("app.api.profile.get_storage_backend") as mock_storage_factory:
            mock_storage_factory.return_value = mock_storage
            with pytest.raises(HTTPException) as exc_info:
                await upload_profile_picture(
                    file=mock_file, current_user=user, db=mock_db, settings=settings
                )

        assert exc_info.value.status_code == 422
