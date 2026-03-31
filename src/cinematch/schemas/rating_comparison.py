"""Pydantic schemas for rating comparison endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class RatingComparisonMovie(BaseModel):
    """A single movie with user vs community rating comparison."""

    movie_id: int
    title: str
    poster_path: str | None
    user_rating: int
    community_avg: float
    difference: float


class RatingComparisonResponse(BaseModel):
    """Rating comparison summary for a user."""

    user_id: int
    user_avg: float
    community_avg: float
    agreement_pct: float
    total_rated: int
    most_overrated: list[RatingComparisonMovie]
    most_underrated: list[RatingComparisonMovie]
