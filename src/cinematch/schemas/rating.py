"""Pydantic schemas for rating endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RatingCreate(BaseModel):
    """Request body for creating/updating a rating."""

    movie_id: int
    rating: float = Field(ge=0.5, le=5.0)


class RatingResponse(BaseModel):
    """Single rating in a response."""

    user_id: int
    movie_id: int
    rating: float
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
