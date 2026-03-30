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
