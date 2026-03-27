"""Pydantic schemas for user endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """User details."""

    id: int
    movielens_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenreCount(BaseModel):
    """Genre with rating count and percentage."""

    genre: str
    count: int
    percentage: float


class RatingBucket(BaseModel):
    """Rating value bucket with count."""

    rating: str
    count: int


class PersonCount(BaseModel):
    """Person (director/actor) with count of rated movies."""

    name: str
    count: int


class MonthlyActivity(BaseModel):
    """Monthly rating activity bucket."""

    month: str
    count: int


class UserStatsResponse(BaseModel):
    """Aggregated user profile analytics."""

    user_id: int
    total_ratings: int
    average_rating: float
    genre_distribution: list[GenreCount]
    rating_distribution: list[RatingBucket]
    top_directors: list[PersonCount]
    top_actors: list[PersonCount]
    rating_timeline: list[MonthlyActivity]
