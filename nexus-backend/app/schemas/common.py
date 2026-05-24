"""Common Pydantic schemas for API responses.

Provides a generic ApiResponse wrapper, a paginated response wrapper,
and a structured ApiErrorResponse for consistent JSON response
formatting across all endpoints.
"""

import math
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class FieldError(BaseModel):
    """A single field-level validation error."""

    field: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    """Generic wrapper for successful API responses."""

    data: T


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic wrapper for paginated API responses.

    Includes the page of items along with pagination metadata.
    """

    items: list[T]
    total: int
    page: int
    size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        size: int,
    ) -> "PaginatedResponse[T]":
        """Build a PaginatedResponse from items and pagination parameters."""
        total_pages = max(1, math.ceil(total / size)) if size > 0 else 1
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )


class ApiErrorResponse(BaseModel):
    """Structured error response with optional field-level details."""

    error: str
    details: list[FieldError] | None = None
