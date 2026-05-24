"""Tests for storage backend interface and implementations."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.storage import get_storage_backend
from app.storage.base import StorageBackend
from app.storage.cloud import CloudStorageBackend
from app.storage.local import LocalStorageBackend


class TestLocalStorageBackend:
    """Tests for LocalStorageBackend."""

    def test_creates_storage_directory(self, tmp_path):
        """Storage directory is created if it does not exist."""
        storage_dir = tmp_path / "new_uploads"
        assert not storage_dir.exists()
        LocalStorageBackend(str(storage_dir))
        assert storage_dir.exists()

    @pytest.mark.asyncio
    async def test_save_writes_file(self, tmp_path):
        """save() writes file bytes to the storage directory."""
        backend = LocalStorageBackend(str(tmp_path))
        data = b"fake image data"
        url = await backend.save("test.jpg", data, "image/jpeg")

        saved_file = tmp_path / "test.jpg"
        assert saved_file.exists()
        assert saved_file.read_bytes() == data
        assert url == "/uploads/test.jpg"

    @pytest.mark.asyncio
    async def test_save_returns_public_url(self, tmp_path):
        """save() returns the correct public URL path."""
        backend = LocalStorageBackend(str(tmp_path))
        url = await backend.save("abc-123.png", b"data", "image/png")
        assert url == "/uploads/abc-123.png"

    @pytest.mark.asyncio
    async def test_save_overwrites_existing_file(self, tmp_path):
        """save() overwrites an existing file with the same name."""
        backend = LocalStorageBackend(str(tmp_path))
        await backend.save("file.jpg", b"original", "image/jpeg")
        await backend.save("file.jpg", b"updated", "image/jpeg")

        assert (tmp_path / "file.jpg").read_bytes() == b"updated"

    @pytest.mark.asyncio
    async def test_delete_removes_file(self, tmp_path):
        """delete() removes the file from the filesystem."""
        backend = LocalStorageBackend(str(tmp_path))
        await backend.save("to_delete.jpg", b"data", "image/jpeg")
        assert (tmp_path / "to_delete.jpg").exists()

        await backend.delete("to_delete.jpg")
        assert not (tmp_path / "to_delete.jpg").exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file_is_noop(self, tmp_path):
        """delete() does not raise when the file does not exist."""
        backend = LocalStorageBackend(str(tmp_path))
        # Should not raise
        await backend.delete("nonexistent.jpg")

    def test_get_public_url(self, tmp_path):
        """get_public_url() returns /uploads/<filename>."""
        backend = LocalStorageBackend(str(tmp_path))
        assert backend.get_public_url("photo.webp") == "/uploads/photo.webp"

    def test_implements_storage_backend_interface(self, tmp_path):
        """LocalStorageBackend is a proper subclass of StorageBackend."""
        backend = LocalStorageBackend(str(tmp_path))
        assert isinstance(backend, StorageBackend)


class TestCloudStorageBackend:
    """Tests for CloudStorageBackend."""

    def _make_backend(
        self,
        bucket: str = "test-bucket",
        region: str = "us-east-1",
        endpoint: str | None = None,
    ) -> CloudStorageBackend:
        return CloudStorageBackend(
            bucket=bucket,
            region=region,
            endpoint=endpoint,
            access_key="test-key",
            secret_key="test-secret",
        )

    def test_implements_storage_backend_interface(self):
        """CloudStorageBackend is a proper subclass of StorageBackend."""
        backend = self._make_backend()
        assert isinstance(backend, StorageBackend)

    def test_get_public_url_default_endpoint(self):
        """get_public_url() returns correct URL with default AWS endpoint."""
        backend = self._make_backend(bucket="my-bucket", region="us-west-2")
        url = backend.get_public_url("photo.jpg")
        assert url == "https://s3.us-west-2.amazonaws.com/my-bucket/photo.jpg"

    def test_get_public_url_custom_endpoint(self):
        """get_public_url() returns correct URL with custom endpoint."""
        backend = self._make_backend(
            bucket="my-bucket",
            endpoint="https://minio.example.com",
        )
        url = backend.get_public_url("photo.jpg")
        assert url == "https://minio.example.com/my-bucket/photo.jpg"

    def test_get_public_url_strips_trailing_slash(self):
        """Custom endpoint trailing slash is stripped."""
        backend = self._make_backend(
            bucket="my-bucket",
            endpoint="https://minio.example.com/",
        )
        url = backend.get_public_url("photo.jpg")
        assert url == "https://minio.example.com/my-bucket/photo.jpg"

    @pytest.mark.asyncio
    async def test_save_uploads_and_returns_url(self):
        """save() sends PUT request and returns the public URL."""
        backend = self._make_backend(bucket="uploads", region="us-east-1")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.storage.cloud.httpx.AsyncClient", return_value=mock_client):
            result = await backend.save("image.jpg", b"image-data", "image/jpeg")

        assert result == "https://s3.us-east-1.amazonaws.com/uploads/image.jpg"
        mock_client.put.assert_called_once_with(
            "https://s3.us-east-1.amazonaws.com/uploads/image.jpg",
            content=b"image-data",
            headers={"Content-Type": "image/jpeg"},
        )

    @pytest.mark.asyncio
    async def test_save_raises_on_http_error(self):
        """save() raises HTTPStatusError on non-2xx response."""
        backend = self._make_backend(bucket="uploads", region="us-east-1")

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Forbidden",
                request=MagicMock(),
                response=mock_response,
            )
        )

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.storage.cloud.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await backend.save("image.jpg", b"image-data", "image/jpeg")

    @pytest.mark.asyncio
    async def test_delete_sends_delete_request(self):
        """delete() sends DELETE request to the correct URL."""
        backend = self._make_backend(bucket="uploads", region="us-east-1")

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.storage.cloud.httpx.AsyncClient", return_value=mock_client):
            await backend.delete("image.jpg")

        mock_client.delete.assert_called_once_with(
            "https://s3.us-east-1.amazonaws.com/uploads/image.jpg"
        )

    @pytest.mark.asyncio
    async def test_delete_noop_on_404(self):
        """delete() does not raise when file is not found (404)."""
        backend = self._make_backend(bucket="uploads", region="us-east-1")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response,
            )
        )

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.storage.cloud.httpx.AsyncClient", return_value=mock_client):
            # Should not raise
            await backend.delete("image.jpg")

    @pytest.mark.asyncio
    async def test_delete_handles_server_error_gracefully(self):
        """delete() logs warning on non-404 errors without raising."""
        backend = self._make_backend(bucket="uploads", region="us-east-1")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=mock_response,
            )
        )

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.storage.cloud.httpx.AsyncClient", return_value=mock_client):
            # Should not raise
            await backend.delete("image.jpg")


class TestGetStorageBackend:
    """Tests for the storage backend factory function."""

    def _set_base_env(self, monkeypatch, tmp_path):
        """Set required env vars for Settings construction."""
        monkeypatch.setenv("NEXUS_MODE", "tracker")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("JWT_SECRET", "test-secret")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
        monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path))

    def test_local_backend_returns_local_storage(self, tmp_path, monkeypatch):
        """Factory returns LocalStorageBackend for LOCAL config."""
        self._set_base_env(monkeypatch, tmp_path)
        monkeypatch.setenv("STORAGE_BACKEND", "local")

        from app.core.config import Settings

        settings = Settings()
        backend = get_storage_backend(settings)
        assert isinstance(backend, LocalStorageBackend)

    def test_cloud_backend_returns_cloud_storage(self, tmp_path, monkeypatch):
        """Factory returns CloudStorageBackend for CLOUD config with valid settings."""
        self._set_base_env(monkeypatch, tmp_path)
        monkeypatch.setenv("STORAGE_BACKEND", "cloud")
        monkeypatch.setenv("CLOUD_STORAGE_BUCKET", "my-bucket")
        monkeypatch.setenv("CLOUD_STORAGE_REGION", "us-east-1")
        monkeypatch.setenv("CLOUD_STORAGE_ENDPOINT", "https://s3.us-east-1.amazonaws.com")
        monkeypatch.setenv("CLOUD_STORAGE_ACCESS_KEY", "test-key")
        monkeypatch.setenv("CLOUD_STORAGE_SECRET_KEY", "test-secret")

        from app.core.config import Settings

        settings = Settings()
        backend = get_storage_backend(settings)
        assert isinstance(backend, CloudStorageBackend)

    def test_cloud_backend_missing_bucket_raises_value_error(self, tmp_path, monkeypatch):
        """Factory raises ValueError when cloud bucket is not configured."""
        self._set_base_env(monkeypatch, tmp_path)
        monkeypatch.setenv("STORAGE_BACKEND", "cloud")
        monkeypatch.setenv("CLOUD_STORAGE_REGION", "us-east-1")

        from app.core.config import Settings

        settings = Settings()
        with pytest.raises(ValueError, match="CLOUD_STORAGE_BUCKET"):
            get_storage_backend(settings)

    def test_cloud_backend_missing_region_raises_value_error(self, tmp_path, monkeypatch):
        """Factory raises ValueError when cloud region is not configured."""
        self._set_base_env(monkeypatch, tmp_path)
        monkeypatch.setenv("STORAGE_BACKEND", "cloud")
        monkeypatch.setenv("CLOUD_STORAGE_BUCKET", "my-bucket")

        from app.core.config import Settings

        settings = Settings()
        with pytest.raises(ValueError, match="CLOUD_STORAGE_REGION"):
            get_storage_backend(settings)
