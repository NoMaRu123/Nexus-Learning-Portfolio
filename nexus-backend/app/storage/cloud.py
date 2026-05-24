"""Cloud object storage backend (S3-compatible).

Stores files in an S3-compatible cloud object storage service using
httpx for HTTP requests. Intended for Portfolio Mode where files are
served from a public cloud bucket.

The backend constructs standard S3 REST API URLs and uses HTTP PUT/DELETE
operations. Authentication is handled via query parameters or headers
depending on the endpoint configuration.

Note: This implementation uses simple HTTP PUT uploads suitable for
S3-compatible services that support unsigned or pre-configured public
write access (e.g., via bucket policies or presigned URLs generated
externally). For production use with AWS Signature V4 authentication,
consider integrating ``boto3`` or a dedicated signing library.
"""

import logging

import httpx

from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class CloudStorageBackend(StorageBackend):
    """Storage backend that persists files to S3-compatible cloud storage.

    Files are uploaded via HTTP PUT to the configured endpoint and bucket.
    Public URLs are constructed from the endpoint, bucket, and filename.

    Args:
        bucket: The S3 bucket name.
        region: The AWS region (e.g. ``us-east-1``).
        endpoint: The S3-compatible endpoint URL (e.g.
            ``https://s3.us-east-1.amazonaws.com``). If not provided,
            defaults to the standard AWS S3 endpoint for the region.
        access_key: The access key for authentication.
        secret_key: The secret key for authentication.
    """

    def __init__(
        self,
        bucket: str,
        region: str,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._region = region
        self._endpoint = (
            endpoint.rstrip("/") if endpoint else f"https://s3.{region}.amazonaws.com"
        )
        self._access_key = access_key
        self._secret_key = secret_key

    @property
    def _base_url(self) -> str:
        """Return the base URL for the bucket."""
        return f"{self._endpoint}/{self._bucket}"

    def _object_url(self, filename: str) -> str:
        """Return the full URL for an object in the bucket."""
        return f"{self._base_url}/{filename}"

    async def save(self, filename: str, data: bytes, content_type: str) -> str:
        """Upload file data to cloud storage and return the public URL.

        Sends an HTTP PUT request to the S3-compatible endpoint with the
        file data and content type header.

        Args:
            filename: The target filename (typically UUID-based).
            data: Raw file bytes to store.
            content_type: MIME type of the file (e.g. ``image/jpeg``).

        Returns:
            The public URL for the uploaded file.

        Raises:
            httpx.HTTPStatusError: If the upload request fails.
        """
        url = self._object_url(filename)
        headers = {"Content-Type": content_type}

        async with httpx.AsyncClient() as client:
            response = await client.put(url, content=data, headers=headers)
            response.raise_for_status()

        logger.info("Uploaded %s to cloud storage: %s", filename, url)
        return self.get_public_url(filename)

    async def delete(self, filename: str) -> None:
        """Delete a file from cloud storage.

        Sends an HTTP DELETE request to the S3-compatible endpoint.
        Logs a warning if the deletion fails but does not raise, matching
        the no-op-on-missing contract of the base interface.

        Args:
            filename: The filename to delete.
        """
        url = self._object_url(filename)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url)
                response.raise_for_status()
            logger.info("Deleted %s from cloud storage", filename)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.debug("File %s not found in cloud storage (already deleted)", filename)
            else:
                logger.warning(
                    "Failed to delete %s from cloud storage: %s",
                    filename,
                    exc.response.status_code,
                )

    def get_public_url(self, filename: str) -> str:
        """Return the public URL for a stored file.

        Args:
            filename: The filename to generate a URL for.

        Returns:
            The full public URL for the file in cloud storage.
        """
        return self._object_url(filename)
