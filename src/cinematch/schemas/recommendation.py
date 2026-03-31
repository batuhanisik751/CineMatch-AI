"""Pydantic schemas for recommendation endpoints."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from cinematch.schemas.movie import MovieSummary


class DiversityLevel(StrEnum):
    """User-facing diversity control for recommendations."""

    low = "low"
    medium = "medium"
    high = "high"


DIVERSITY_LAMBDA_MAP: dict[DiversityLevel, float] = {
    DiversityLevel.low: 0.9,
    DiversityLevel.medium: 0.7,
    DiversityLevel.high: 0.4,
}


class SeedInfluenceSchema(BaseModel):
    """Which seed movie contributed most to a recommendation."""

    movie_id: int
    title: str
    your_rating: float


class ScoreBreakdownSchema(BaseModel):
    """Decomposition of the hybrid score."""

    content_score: float
    collab_score: float
    alpha: float


class RecommendationItem(BaseModel):
    """Single recommendation with scores and explanations."""

    movie: MovieSummary
    score: float
    content_score: float | None = None
    collab_score: float | None = None
    because_you_liked: SeedInfluenceSchema | None = None
    feature_explanations: list[str] = Field(default_factory=list)
    score_breakdown: ScoreBreakdownSchema | None = None


class RecommendationsResponse(BaseModel):
    """List of recommendations for a user."""

    user_id: int
    strategy: str
    diversity: str = "medium"
    recommendations: list[RecommendationItem]


class RecommendationExplanation(BaseModel):
    """LLM-generated explanation for a recommendation."""

    movie_id: int
    title: str
    explanation: str
    score: float


class FromSeedRecommendationsResponse(RecommendationsResponse):
    """Recommendations seeded from a specific movie."""

    seed_movie: MovieSummary


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
