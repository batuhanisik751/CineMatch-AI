"""Service layer for CineMatch-AI recommendation engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cinematch.services.hybrid_recommender import HybridRecommender
from cinematch.services.movie_service import MovieService
from cinematch.services.rating_service import RatingService
from cinematch.services.watchlist_service import WatchlistService

if TYPE_CHECKING:
    from cinematch.services.collab_recommender import CollabRecommender
    from cinematch.services.content_recommender import ContentRecommender
    from cinematch.services.embedding_service import EmbeddingService

__all__ = [
    "CollabRecommender",
    "ContentRecommender",
    "EmbeddingService",
    "HybridRecommender",
    "MovieService",
    "RatingService",
    "WatchlistService",
]
