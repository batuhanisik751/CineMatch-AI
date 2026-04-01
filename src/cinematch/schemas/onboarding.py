"""Pydantic schemas for onboarding endpoints."""

from __future__ import annotations

from pydantic import BaseModel

from cinematch.schemas.movie import MovieSummary


class OnboardingMoviesResponse(BaseModel):
    """List of genre-diverse popular movies for onboarding."""

    movies: list[MovieSummary]
    total: int
    user_id: int


class OnboardingStatusResponse(BaseModel):
    """Whether the user has completed onboarding."""

    user_id: int
    completed: bool
    rating_count: int
    threshold: int
