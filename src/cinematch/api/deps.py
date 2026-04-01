"""FastAPI dependency injection helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from cinematch.db.session import get_db

if TYPE_CHECKING:
    from cinematch.core.cache import CacheService
    from cinematch.services.content_recommender import ContentRecommender
    from cinematch.services.dismissal_service import DismissalService
    from cinematch.services.embedding_service import EmbeddingService
    from cinematch.services.feed_service import FeedService
    from cinematch.services.global_stats_service import GlobalStatsService
    from cinematch.services.hybrid_recommender import HybridRecommender
    from cinematch.services.llm_service import LLMService
    from cinematch.services.movie_service import MovieService
    from cinematch.services.rating_comparison_service import RatingComparisonService
    from cinematch.services.rating_service import RatingService
    from cinematch.services.streak_service import StreakService
    from cinematch.services.taste_evolution_service import TasteEvolutionService
    from cinematch.services.taste_profile_service import TasteProfileService
    from cinematch.services.user_list_service import UserListService
    from cinematch.services.user_stats_service import UserStatsService
    from cinematch.services.watchlist_service import WatchlistService

# Re-export get_db so routes can import from one place
__all__ = ["get_db"]


def get_movie_service(request: Request) -> MovieService:
    return request.app.state.movie_service


def get_rating_service(request: Request) -> RatingService:
    return request.app.state.rating_service


def get_content_recommender(request: Request) -> ContentRecommender | None:
    return getattr(request.app.state, "content_recommender", None)


def get_hybrid_recommender(request: Request) -> HybridRecommender | None:
    return getattr(request.app.state, "hybrid_recommender", None)


def get_cache_service(request: Request) -> CacheService | None:
    return getattr(request.app.state, "cache_service", None)


def get_embedding_service(request: Request) -> EmbeddingService | None:
    return getattr(request.app.state, "embedding_service", None)


def get_llm_service(request: Request) -> LLMService | None:
    return getattr(request.app.state, "llm_service", None)


def get_user_stats_service(request: Request) -> UserStatsService:
    return request.app.state.user_stats_service


def get_watchlist_service(request: Request) -> WatchlistService:
    return request.app.state.watchlist_service


def get_dismissal_service(request: Request) -> DismissalService:
    return request.app.state.dismissal_service


def get_feed_service(request: Request) -> FeedService:
    return request.app.state.feed_service


def get_taste_profile_service(request: Request) -> TasteProfileService:
    return request.app.state.taste_profile_service


def get_rating_comparison_service(request: Request) -> RatingComparisonService:
    return request.app.state.rating_comparison_service


def get_streak_service(request: Request) -> StreakService:
    return request.app.state.streak_service


def get_taste_evolution_service(request: Request) -> TasteEvolutionService:
    return request.app.state.taste_evolution_service


def get_global_stats_service(request: Request) -> GlobalStatsService:
    return request.app.state.global_stats_service


def get_user_list_service(request: Request) -> UserListService:
    return request.app.state.user_list_service
