"""Abstract storage backend interface.

Defines the contract for file storage operations used by the profile
picture upload flow and any other file storage needs. Concrete
implementations (local filesystem, cloud object storage) implement
this interface and are selected at startup via the STORAGE_BACKEND
environment variable.
"""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Abstract base class for file storage backends.

    All storage backends must implement save, delete, and get_public_url
    to provide a consistent interface regardless of the underlying
    storage mechanism.
    """

    @abstractmethod
    async def save(self, filename: str, data: bytes, content_type: str) -> str:
        """Save file data and return the public URL.

        Args:
            filename: The target filename (typically UUID-based).
            data: Raw file bytes to store.
            content_type: MIME type of the file (e.g. "image/jpeg").

        Returns:
            The public URL where the file can be accessed.
        """
        ...

    @abstractmethod
    async def delete(self, filename: str) -> None:
        """Delete a file from storage.

        If the file does not exist, this method is a no-op.

        Args:
            filename: The filename to delete.
        """
        ...

    @abstractmethod
    def get_public_url(self, filename: str) -> str:
        """Return the public URL for a stored file.

        Args:
            filename: The filename to generate a URL for.

        Returns:
            A URL path or full URL where the file is accessible.
        """
        ...
