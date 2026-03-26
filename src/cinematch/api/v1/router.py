"""Aggregate all v1 API routers."""

from __future__ import annotations

from fastapi import APIRouter

from cinematch.api.v1 import movies, ratings, recommendations, users

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(movies.router, prefix="/movies", tags=["movies"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(ratings.router, tags=["ratings"])
api_v1_router.include_router(recommendations.router, tags=["recommendations"])
