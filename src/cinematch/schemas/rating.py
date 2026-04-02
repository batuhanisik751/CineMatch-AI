"""Pydantic schemas for rating endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RatingCreate(BaseModel):
    """Request body for creating/updating a rating."""

    movie_id: int
    rating: int = Field(ge=1, le=10)


class RatingResponse(BaseModel):
    """Single rating in a response."""

    user_id: int
    movie_id: int
    rating: int
    timestamp: datetime
    movie_title: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserRatingsResponse(BaseModel):
    """Paginated list of user ratings."""

    user_id: int
    ratings: list[RatingResponse]
    total: int
    offset: int
    limit: int


class RatingBulkCheckResponse(BaseModel):
    """Map of movie_id -> rating for bulk check."""

    ratings: dict[int, int]


class ImportSource(StrEnum):
    """Supported CSV import sources."""

    LETTERBOXD = "letterboxd"
    IMDB = "imdb"
    AUTO = "auto"


class ImportResultItem(BaseModel):
    """Result for a single row in a CSV import."""

    title: str
    year: int | None = None
    original_rating: float
    scaled_rating: int
    movie_id: int | None = None
    status: Literal["imported", "updated", "not_found"]


class ImportResponse(BaseModel):
    """Response for a CSV import operation."""

    user_id: int
    source: str
    total_rows: int
    imported: int
    updated: int
    not_found: int
    results: list[ImportResultItem]


class DiaryDayMovie(BaseModel):
    """A single movie entry within a diary day."""

    id: int
    title: str | None = None
    rating: int


class DiaryDay(BaseModel):
    """Aggregated rating activity for a single day."""

    date: str
    count: int
    movies: list[DiaryDayMovie]


class DiaryResponse(BaseModel):
    """Film diary / rating calendar for a given year."""

    user_id: int
    year: int
    days: list[DiaryDay]
    total_ratings: int
