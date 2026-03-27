"""Pydantic schemas for watchlist endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WatchlistAdd(BaseModel):
    """Request body for adding a movie to the watchlist."""

    movie_id: int


class WatchlistItemResponse(BaseModel):
    """Single watchlist item in a response."""

    user_id: int
    movie_id: int
    added_at: datetime
    movie_title: str | None = None
    poster_path: str | None = None
    genres: list[str] = []
    vote_average: float = 0.0
    release_date: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WatchlistResponse(BaseModel):
    """Paginated list of watchlist items."""

    user_id: int
    items: list[WatchlistItemResponse]
    total: int
    offset: int
    limit: int


class WatchlistBulkStatusResponse(BaseModel):
    """Bulk watchlist status check result."""

    movie_ids: list[int]
