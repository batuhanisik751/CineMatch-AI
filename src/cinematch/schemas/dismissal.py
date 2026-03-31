"""Pydantic schemas for dismissal endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DismissalCreate(BaseModel):
    """Request body for dismissing a movie."""

    movie_id: int


class DismissalResponse(BaseModel):
    """Single dismissal in a response."""

    user_id: int
    movie_id: int
    dismissed_at: datetime
    movie_title: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DismissalItemResponse(BaseModel):
    """Single dismissed movie with details."""

    user_id: int
    movie_id: int
    dismissed_at: datetime
    movie_title: str | None = None
    poster_path: str | None = None
    genres: list[str] = []
    vote_average: float = 0.0
    release_date: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DismissalListResponse(BaseModel):
    """Paginated list of dismissed movies."""

    user_id: int
    items: list[DismissalItemResponse]
    total: int
    offset: int
    limit: int


class DismissalBulkStatusResponse(BaseModel):
    """Bulk dismissal status check result."""

    movie_ids: list[int]
