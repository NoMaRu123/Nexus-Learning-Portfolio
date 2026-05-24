"""Tests for app.services.profile module.

Validates ProfileService operations including profile retrieval,
updates, picture upload with EXIF stripping, and public profile access.
"""

import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from app.models.profile import UserProfile
from app.schemas.profile import ProfileUpdate
from app.services.exceptions import InvalidMimeTypeError, ProfileNotFoundError
from app.services.profile import ALLOWED_MIME_TYPES, ProfileService


def _make_profile(
    user_id: uuid.UUID,
    name: str | None = "Test User",
    bio: str | None = "A test bio",
    contact_email: str | None = "test@example.com",
    social_links: dict | None = None,
    picture_url: str | None = None,
    profile_id: uuid.UUID | None = None,
) -> UserProfile:
    """Factory for creating UserProfile instances for testing."""
    profile = UserProfile(
        id=profile_id or uuid.uuid4(),
        user_id=user_id,
        name=name,
        bio=bio,
        contact_email=contact_email,
        social_links=social_links or {},
        picture_url=picture_url,
        updated_at=datetime.now(timezone.utc),
    )
    return profile


def _mock_db_no_result() -> AsyncMock:
    """Create a mock DB session where execute returns no rows."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mock_db.add = MagicMock()
    return mock_db


def _mock_db_with_result(record: object) -> AsyncMock:
    """Create a mock DB session where execute returns a single record."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = record
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mock_db.add = MagicMock()
    return mock_db


def _mock_storage(save_url: str = "/uploads/new-pic.jpg") -> AsyncMock:
    """Create a mock StorageBackend."""
    storage = AsyncMock()
    storage.save.return_value = save_url
    storage.delete = AsyncMock()
    return storage


def _make_test_image(fmt: str = "JPEG", size: tuple[int, int] = (100, 100)) -> bytes:
    """Create a minimal test image in the specified format."""
    image = Image.new("RGB", size, color=(255, 0, 0))
    buf = io.BytesIO()
    image.save(buf, format=fmt)
    return buf.getvalue()


def _make_image_with_exif() -> bytes:
    """Create a JPEG image with EXIF metadata for testing stripping.

    Uses Pillow's built-in Exif class to embed metadata without
    requiring the piexif library.
    """
    image = Image.new("RGB", (100, 100), color=(0, 128, 255))
    exif = image.getexif()
    # Tag 271 = Make (camera manufacturer)
    exif[271] = "TestCamera"
    # Tag 305 = Software
    exif[305] = "TestSoftware"
    buf = io.BytesIO()
    image.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


class TestProfileServiceGetProfile:
    """Tests for ProfileService.get_profile()."""

    @pytest.mark.asyncio
    async def test_get_profile_returns_profile(self):
        """get_profile returns the UserProfile for the authenticated user."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        mock_db = _mock_db_with_result(profile)
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        result = await service.get_profile()

        assert result.user_id == user_id
        assert result.name == "Test User"
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_profile_not_found_raises_error(self):
        """get_profile raises ProfileNotFoundError when no profile exists."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)

        with pytest.raises(ProfileNotFoundError) as exc_info:
            await service.get_profile()

        assert str(user_id) in str(exc_info.value)


class TestProfileServiceUpdateProfile:
    """Tests for ProfileService.update_profile()."""

    @pytest.mark.asyncio
    async def test_update_profile_modifies_provided_fields(self):
        """update_profile only changes fields that are set in the update data."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id, name="Old Name", bio="Old bio")
        mock_db = _mock_db_with_result(profile)

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        data = ProfileUpdate(name="New Name")

        result = await service.update_profile(data)

        assert result.name == "New Name"
        assert result.bio == "Old bio"  # Unchanged
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_profile_with_valid_email(self):
        """update_profile stores a valid contact email."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        mock_db = _mock_db_with_result(profile)

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        data = ProfileUpdate(contact_email="new@example.com")

        result = await service.update_profile(data)

        assert result.contact_email == "new@example.com"

    @pytest.mark.asyncio
    async def test_update_profile_not_found_raises_error(self):
        """update_profile raises ProfileNotFoundError when no profile exists."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        data = ProfileUpdate(name="New Name")

        with pytest.raises(ProfileNotFoundError):
            await service.update_profile(data)

    @pytest.mark.asyncio
    async def test_update_profile_with_social_links(self):
        """update_profile stores social links as a dict."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        mock_db = _mock_db_with_result(profile)

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        links = {"github": "https://github.com/testuser", "linkedin": "https://linkedin.com/in/testuser"}
        data = ProfileUpdate(social_links=links)

        result = await service.update_profile(data)

        assert result.social_links == links


class TestProfileServiceUploadPicture:
    """Tests for ProfileService.upload_picture()."""

    @pytest.mark.asyncio
    async def test_upload_validates_mime_type_allowlist(self):
        """upload_picture rejects MIME types not in the allowlist."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        mock_db = _mock_db_with_result(profile)
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)

        with pytest.raises(InvalidMimeTypeError) as exc_info:
            await service.upload_picture(b"fake", "image/gif", "photo.gif")

        assert "image/gif" in str(exc_info.value)
        storage.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_upload_accepts_jpeg(self):
        """upload_picture accepts image/jpeg MIME type."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        mock_db = _mock_db_with_result(profile)

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        new_url = "/uploads/new-pic.jpg"
        storage = _mock_storage(save_url=new_url)

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        file_data = _make_test_image("JPEG")

        result = await service.upload_picture(file_data, "image/jpeg", "photo.jpg")

        assert result == new_url
        storage.save.assert_awaited_once()
        # Verify the filename has .jpg extension
        saved_filename = storage.save.call_args[0][0]
        assert saved_filename.endswith(".jpg")

    @pytest.mark.asyncio
    async def test_upload_accepts_png(self):
        """upload_picture accepts image/png MIME type."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        mock_db = _mock_db_with_result(profile)

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        storage = _mock_storage(save_url="/uploads/new-pic.png")

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        file_data = _make_test_image("PNG")

        result = await service.upload_picture(file_data, "image/png", "photo.png")

        assert result == "/uploads/new-pic.png"
        saved_filename = storage.save.call_args[0][0]
        assert saved_filename.endswith(".png")

    @pytest.mark.asyncio
    async def test_upload_accepts_webp(self):
        """upload_picture accepts image/webp MIME type."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        mock_db = _mock_db_with_result(profile)

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        storage = _mock_storage(save_url="/uploads/new-pic.webp")

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        file_data = _make_test_image("WEBP")

        result = await service.upload_picture(file_data, "image/webp", "photo.webp")

        assert result == "/uploads/new-pic.webp"
        saved_filename = storage.save.call_args[0][0]
        assert saved_filename.endswith(".webp")

    @pytest.mark.asyncio
    async def test_upload_generates_uuid_filename(self):
        """upload_picture generates a UUID-based filename."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        mock_db = _mock_db_with_result(profile)

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        file_data = _make_test_image("JPEG")

        await service.upload_picture(file_data, "image/jpeg", "photo.jpg")

        saved_filename = storage.save.call_args[0][0]
        # Filename should be UUID + extension
        name_part = saved_filename.rsplit(".", 1)[0]
        uuid.UUID(name_part)  # Raises ValueError if not a valid UUID

    @pytest.mark.asyncio
    async def test_upload_deletes_previous_picture(self):
        """upload_picture deletes the old picture when one exists."""
        user_id = uuid.uuid4()
        old_url = "/uploads/old-pic.jpg"
        profile = _make_profile(user_id, picture_url=old_url)
        mock_db = _mock_db_with_result(profile)

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        storage = _mock_storage(save_url="/uploads/new-pic.jpg")

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        file_data = _make_test_image("JPEG")

        await service.upload_picture(file_data, "image/jpeg", "photo.jpg")

        storage.delete.assert_awaited_once_with("old-pic.jpg")

    @pytest.mark.asyncio
    async def test_upload_no_delete_when_no_previous_picture(self):
        """upload_picture does not call delete when there is no previous picture."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id, picture_url=None)
        mock_db = _mock_db_with_result(profile)

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        file_data = _make_test_image("JPEG")

        await service.upload_picture(file_data, "image/jpeg", "photo.jpg")

        storage.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_upload_updates_profile_picture_url(self):
        """upload_picture updates the profile's picture_url field."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id, picture_url=None)
        mock_db = _mock_db_with_result(profile)

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        new_url = "/uploads/brand-new.jpg"
        storage = _mock_storage(save_url=new_url)

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        file_data = _make_test_image("JPEG")

        await service.upload_picture(file_data, "image/jpeg", "photo.jpg")

        assert profile.picture_url == new_url

    @pytest.mark.asyncio
    async def test_upload_strips_exif_metadata(self):
        """upload_picture strips EXIF metadata from the image."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        mock_db = _mock_db_with_result(profile)

        async def mock_refresh(obj: UserProfile) -> None:
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = mock_refresh
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)

        # Create image with EXIF data
        image_with_exif = _make_image_with_exif()

        # Verify the source image has EXIF
        src_image = Image.open(io.BytesIO(image_with_exif))
        assert src_image.info.get("exif") is not None

        await service.upload_picture(image_with_exif, "image/jpeg", "photo.jpg")

        # The data passed to storage.save should have EXIF stripped
        saved_data = storage.save.call_args[0][1]
        cleaned_image = Image.open(io.BytesIO(saved_data))
        assert cleaned_image.info.get("exif") is None

    @pytest.mark.asyncio
    async def test_upload_not_found_raises_error(self):
        """upload_picture raises ProfileNotFoundError when no profile exists."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        file_data = _make_test_image("JPEG")

        with pytest.raises(ProfileNotFoundError):
            await service.upload_picture(file_data, "image/jpeg", "photo.jpg")


class TestProfileServiceGetPublicProfile:
    """Tests for ProfileService.get_public_profile()."""

    @pytest.mark.asyncio
    async def test_get_public_profile_returns_profile(self):
        """get_public_profile returns the UserProfile for public display."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        mock_db = _mock_db_with_result(profile)
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)
        result = await service.get_public_profile()

        assert result.user_id == user_id
        assert result.name == "Test User"

    @pytest.mark.asyncio
    async def test_get_public_profile_not_found_raises_error(self):
        """get_public_profile raises ProfileNotFoundError when no profile exists."""
        user_id = uuid.uuid4()
        mock_db = _mock_db_no_result()
        storage = _mock_storage()

        service = ProfileService(db=mock_db, user_id=user_id, storage=storage)

        with pytest.raises(ProfileNotFoundError):
            await service.get_public_profile()


class TestProfileServiceHelpers:
    """Tests for ProfileService static helper methods."""

    def test_extract_filename_from_relative_url(self):
        """_extract_filename extracts filename from /uploads/file.jpg."""
        result = ProfileService._extract_filename("/uploads/abc-123.jpg")
        assert result == "abc-123.jpg"

    def test_extract_filename_from_absolute_url(self):
        """_extract_filename extracts filename from a full URL."""
        result = ProfileService._extract_filename("https://cdn.example.com/uploads/abc.png")
        assert result == "abc.png"

    def test_extract_filename_from_empty_string(self):
        """_extract_filename returns None for empty string."""
        result = ProfileService._extract_filename("")
        assert result is None

    def test_extract_filename_from_none(self):
        """_extract_filename returns None for None-like empty input."""
        result = ProfileService._extract_filename("")
        assert result is None

    def test_strip_exif_removes_metadata(self):
        """_strip_exif produces an image without EXIF data."""
        image_with_exif = _make_image_with_exif()

        cleaned = ProfileService._strip_exif(image_with_exif, "image/jpeg")

        cleaned_image = Image.open(io.BytesIO(cleaned))
        assert cleaned_image.info.get("exif") is None

    def test_strip_exif_preserves_image_content(self):
        """_strip_exif preserves the image dimensions and mode."""
        original_data = _make_test_image("JPEG", size=(200, 150))

        cleaned = ProfileService._strip_exif(original_data, "image/jpeg")

        original = Image.open(io.BytesIO(original_data))
        cleaned_img = Image.open(io.BytesIO(cleaned))
        assert cleaned_img.size == original.size
        assert cleaned_img.mode == original.mode
