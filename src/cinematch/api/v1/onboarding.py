"""Onboarding endpoints — movie selection and status check."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_current_user, get_db, get_onboarding_service
from cinematch.config import get_settings
from cinematch.models.user import User
from cinematch.schemas.movie import MovieSummary
from cinematch.schemas.onboarding import OnboardingMoviesResponse, OnboardingStatusResponse
from cinematch.services.onboarding_service import OnboardingService

router = APIRouter()


@router.get("/movies", response_model=OnboardingMoviesResponse)
async def get_onboarding_movies(
    current_user: User = Depends(get_current_user),
    count: int = Query(default=20, ge=10, le=30, description="Number of movies to return"),
    db: AsyncSession = Depends(get_db),
    onboarding_service: OnboardingService = Depends(get_onboarding_service),
):
    """Return genre-diverse popular movies for onboarding."""
    user_id = current_user.id
    movies = await onboarding_service.get_onboarding_movies(user_id, count, db)
    return OnboardingMoviesResponse(
        movies=[MovieSummary.model_validate(m) for m in movies],
        total=len(movies),
        user_id=user_id,
    )


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    onboarding_service: OnboardingService = Depends(get_onboarding_service),
):
    """Check whether the user has completed onboarding."""
    settings = get_settings()
    user_id = current_user.id
    status = await onboarding_service.get_onboarding_status(
        user_id, settings.onboarding_threshold, db
    )
    return OnboardingStatusResponse(**status)
