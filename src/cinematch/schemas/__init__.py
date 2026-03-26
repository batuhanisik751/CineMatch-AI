"""Pydantic schemas for request/response validation."""

from cinematch.schemas.movie import (
    MovieResponse,
    MovieSearchResponse,
    MovieSummary,
    SimilarMovie,
    SimilarMoviesResponse,
)
from cinematch.schemas.rating import RatingCreate, RatingResponse, UserRatingsResponse
from cinematch.schemas.recommendation import RecommendationItem, RecommendationsResponse
from cinematch.schemas.user import UserResponse

__all__ = [
    "MovieResponse",
    "MovieSearchResponse",
    "MovieSummary",
    "RatingCreate",
    "RatingResponse",
    "RecommendationItem",
    "RecommendationsResponse",
    "SimilarMovie",
    "SimilarMoviesResponse",
    "UserRatingsResponse",
    "UserResponse",
]
