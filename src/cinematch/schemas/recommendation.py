"""Pydantic schemas for recommendation endpoints."""

from __future__ import annotations

from pydantic import BaseModel

from cinematch.schemas.movie import MovieSummary


class RecommendationItem(BaseModel):
    """Single recommendation with scores."""

    movie: MovieSummary
    score: float
    content_score: float | None = None
    collab_score: float | None = None


class RecommendationsResponse(BaseModel):
    """List of recommendations for a user."""

    user_id: int
    strategy: str
    recommendations: list[RecommendationItem]
