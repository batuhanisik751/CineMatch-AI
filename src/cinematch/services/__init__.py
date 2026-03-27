"""Service layer for CineMatch-AI recommendation engine."""

from cinematch.services.collab_recommender import CollabRecommender
from cinematch.services.content_recommender import ContentRecommender
from cinematch.services.embedding_service import EmbeddingService
from cinematch.services.hybrid_recommender import HybridRecommender
from cinematch.services.movie_service import MovieService
from cinematch.services.rating_service import RatingService
from cinematch.services.watchlist_service import WatchlistService

__all__ = [
    "CollabRecommender",
    "ContentRecommender",
    "EmbeddingService",
    "HybridRecommender",
    "MovieService",
    "RatingService",
    "WatchlistService",
]
