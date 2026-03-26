"""FastAPI dependency injection helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from cinematch.db.session import get_db

if TYPE_CHECKING:
    from cinematch.core.cache import CacheService
    from cinematch.services.content_recommender import ContentRecommender
    from cinematch.services.hybrid_recommender import HybridRecommender
    from cinematch.services.llm_service import LLMService
    from cinematch.services.movie_service import MovieService
    from cinematch.services.rating_service import RatingService

# Re-export get_db so routes can import from one place
__all__ = ["get_db"]


def get_movie_service(request: Request) -> MovieService:
    return request.app.state.movie_service


def get_rating_service(request: Request) -> RatingService:
    return request.app.state.rating_service


def get_content_recommender(request: Request) -> ContentRecommender:
    return request.app.state.content_recommender


def get_hybrid_recommender(request: Request) -> HybridRecommender:
    return request.app.state.hybrid_recommender


def get_cache_service(request: Request) -> CacheService | None:
    return getattr(request.app.state, "cache_service", None)


def get_llm_service(request: Request) -> LLMService | None:
    return getattr(request.app.state, "llm_service", None)
