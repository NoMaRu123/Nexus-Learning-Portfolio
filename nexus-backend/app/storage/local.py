"""Local filesystem storage backend.

Stores files on the local filesystem under a configurable directory.
Intended for Tracker Mode where files are served directly from disk.
"""

from pathlib import Path

from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Storage backend that persists files to the local filesystem.

    Files are written to the directory specified by ``storage_path``,
    which corresponds to the ``STORAGE_LOCAL_PATH`` environment variable.
    Public URLs are returned as ``/uploads/<filename>`` paths suitable
    for serving via a static file mount or reverse proxy.
    """

    def __init__(self, storage_path: str) -> None:
        """Initialize the local storage backend.

        Args:
            storage_path: Filesystem directory where files are stored.
                          Created automatically if it does not exist.
        """
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)

    async def save(self, filename: str, data: bytes, content_type: str) -> str:
        """Write file data to the local filesystem and return the public URL.

        Args:
            filename: The target filename (typically UUID-based).
            data: Raw file bytes to store.
            content_type: MIME type of the file (unused for local storage
                          but accepted for interface consistency).

        Returns:
            The public URL path for the saved file.
        """
        file_path = self._storage_path / filename
        file_path.write_bytes(data)
        return self.get_public_url(filename)

    async def delete(self, filename: str) -> None:
        """Remove a file from the local filesystem.

        No-op if the file does not exist.

        Args:
            filename: The filename to delete.
        """
        file_path = self._storage_path / filename
        if file_path.exists():
            file_path.unlink()

    def get_public_url(self, filename: str) -> str:
        """Return the public URL path for a stored file.

        Args:
            filename: The filename to generate a URL for.

        Returns:
            A URL path in the form ``/uploads/<filename>``.
        """
        return f"/uploads/{filename}"
