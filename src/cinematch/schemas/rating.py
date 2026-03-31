"""Pydantic schemas for rating endpoints."""

from __future__ import annotations

from datetime import datetime

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
