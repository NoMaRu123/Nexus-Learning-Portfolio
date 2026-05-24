"""Storage backend factory.

Provides ``get_storage_backend()`` which selects the appropriate
storage implementation based on the ``STORAGE_BACKEND`` environment
variable configured in application settings.
"""

from app.core.config import Settings, StorageBackendType
from app.storage.base import StorageBackend
from app.storage.cloud import CloudStorageBackend
from app.storage.local import LocalStorageBackend


def get_storage_backend(settings: Settings) -> StorageBackend:
    """Create and return the configured storage backend.

    Args:
        settings: Application settings containing storage configuration.

    Returns:
        A concrete ``StorageBackend`` instance.

    Raises:
        ValueError: If the configured backend type is unrecognized, or
            if cloud storage is selected but required configuration
            (bucket and region) is missing.
    """
    if settings.storage_backend == StorageBackendType.LOCAL:
        return LocalStorageBackend(settings.storage_local_path)
    elif settings.storage_backend == StorageBackendType.CLOUD:
        if not settings.cloud_storage_bucket or not settings.cloud_storage_region:
            raise ValueError(
                "CLOUD_STORAGE_BUCKET and CLOUD_STORAGE_REGION are required "
                "when STORAGE_BACKEND=cloud"
            )
        return CloudStorageBackend(
            bucket=settings.cloud_storage_bucket,
            region=settings.cloud_storage_region,
            endpoint=settings.cloud_storage_endpoint,
            access_key=settings.cloud_storage_access_key,
            secret_key=settings.cloud_storage_secret_key,
        )
    else:
        raise ValueError(f"Unknown storage backend: {settings.storage_backend}")
