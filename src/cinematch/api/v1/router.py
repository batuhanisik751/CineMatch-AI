"""Aggregate all v1 API routers."""

from __future__ import annotations

from fastapi import APIRouter

from cinematch.api.v1 import (
    auth,
    challenges,
    dismissals,
    lists,
    movies,
    onboarding,
    predictions,
    ratings,
    recommendations,
    stats,
    users,
    watchlist,
)

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(movies.router, prefix="/movies", tags=["movies"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(ratings.router, tags=["ratings"])
api_v1_router.include_router(recommendations.router, tags=["recommendations"])
api_v1_router.include_router(watchlist.router, tags=["watchlist"])
api_v1_router.include_router(dismissals.router, tags=["dismissals"])
api_v1_router.include_router(lists.router, tags=["lists"])
api_v1_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_v1_router.include_router(challenges.router, prefix="/challenges", tags=["challenges"])
api_v1_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_v1_router.include_router(predictions.router, tags=["predictions"])
