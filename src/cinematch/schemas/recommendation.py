"""Pydantic schemas for recommendation endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

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


class RecommendationExplanation(BaseModel):
    """LLM-generated explanation for a recommendation."""

    movie_id: int
    title: str
    explanation: str
    score: float


class MoodRecommendationRequest(BaseModel):
    """Request body for mood-based recommendations."""

    mood: str = Field(min_length=1, max_length=200)
    user_id: int
    alpha: float = Field(default=0.3, ge=0.0, le=1.0)
    limit: int = Field(default=20, ge=1, le=100)


class MoodRecommendationItem(BaseModel):
    """Single mood recommendation result."""

    movie: MovieSummary
    similarity: float


class MoodRecommendationResponse(BaseModel):
    """Response for mood-based recommendations."""

    user_id: int
    mood: str
    alpha: float
    is_personalized: bool
    results: list[MoodRecommendationItem]
    total: int
