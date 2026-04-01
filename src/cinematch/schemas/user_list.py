"""Pydantic schemas for custom user lists."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserListCreate(BaseModel):
    """Request body for creating a new list."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    is_public: bool = False


class UserListUpdate(BaseModel):
    """Request body for updating list metadata (PATCH — all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    is_public: bool | None = None


class UserListItemAdd(BaseModel):
    """Request body for adding a movie to a list."""

    movie_id: int


class UserListItemReorder(BaseModel):
    """Request body for reordering list items."""

    movie_ids: list[int] = Field(min_length=1)


class UserListItemResponse(BaseModel):
    """Single item in a list response, enriched with movie details."""

    movie_id: int
    position: int
    added_at: datetime
    movie_title: str | None = None
    poster_path: str | None = None
    genres: list[str] = []
    vote_average: float = 0.0
    release_date: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Summary of a single list (without items)."""

    id: int
    user_id: int
    name: str
    description: str | None = None
    is_public: bool
    movie_count: int = 0
    preview_posters: list[str] = []
    created_at: datetime
    updated_at: datetime


class UserListDetailResponse(BaseModel):
    """Full list detail with paginated items."""

    id: int
    user_id: int
    name: str
    description: str | None = None
    is_public: bool
    movie_count: int = 0
    items: list[UserListItemResponse] = []
    total: int = 0
    offset: int = 0
    limit: int = 20
    created_at: datetime
    updated_at: datetime


class UserListsResponse(BaseModel):
    """All lists for a user."""

    user_id: int
    lists: list[UserListResponse]
    total: int


class PopularListsResponse(BaseModel):
    """Paginated popular public lists."""

    lists: list[UserListResponse]
    total: int
    offset: int
    limit: int
