"""FastAPI application factory with lifespan events."""

from __future__ import annotations

import logging
import pickle
from contextlib import asynccontextmanager

import faiss
import scipy.sparse as sp
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from cinematch import __version__
from cinematch.api.v1.router import api_v1_router
from cinematch.config import get_settings
from cinematch.core.cache import CacheService
from cinematch.core.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    catch_all_handler,
    not_found_handler,
    service_unavailable_handler,
)
from cinematch.core.logging import setup_logging
from cinematch.core.middleware import SecurityHeadersMiddleware
from cinematch.core.rate_limit import limiter
from cinematch.services.achievement_service import AchievementService
from cinematch.services.bingo_service import BingoService
from cinematch.services.blind_spot_service import BlindSpotService
from cinematch.services.challenge_service import ChallengeService
from cinematch.services.collab_recommender import CollabRecommender
from cinematch.services.content_recommender import ContentRecommender
from cinematch.services.dismissal_service import DismissalService
from cinematch.services.embedding_service import EmbeddingService
from cinematch.services.feed_service import FeedService
from cinematch.services.global_stats_service import GlobalStatsService
from cinematch.services.hybrid_recommender import HybridRecommender
from cinematch.services.movie_service import MovieService
from cinematch.services.onboarding_service import OnboardingService
from cinematch.services.rating_comparison_service import RatingComparisonService
from cinematch.services.rating_service import RatingService
from cinematch.services.rewatch_service import RewatchService
from cinematch.services.streak_service import StreakService
from cinematch.services.taste_evolution_service import TasteEvolutionService
from cinematch.services.taste_profile_service import TasteProfileService
from cinematch.services.thematic_collection_service import ThematicCollectionService
from cinematch.services.user_list_service import UserListService
from cinematch.services.user_stats_service import UserStatsService
from cinematch.services.watchlist_service import WatchlistService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(debug=settings.debug)

    try:
        # Load embedding service
        logger.info("Loading embedding model: %s", settings.embedding_model_name)
        embedding_service = EmbeddingService(
            model_name=settings.embedding_model_name,
            batch_size=settings.embedding_batch_size,
        )

        # Load FAISS artifacts
        logger.info("Loading FAISS index from %s", settings.faiss_index_path)
        faiss_index = faiss.read_index(settings.faiss_index_path)
        with open(settings.faiss_id_map_path, "rb") as f:
            faiss_id_map = pickle.load(f)  # noqa: S301

        # Load ALS artifacts
        logger.info("Loading ALS model from %s", settings.als_model_path)
        with open(settings.als_model_path, "rb") as f:
            als_model = pickle.load(f)  # noqa: S301
        with open(settings.als_user_map_path, "rb") as f:
            als_user_map = pickle.load(f)  # noqa: S301
        with open(settings.als_item_map_path, "rb") as f:
            als_item_map = pickle.load(f)  # noqa: S301
        als_user_items = sp.load_npz(settings.als_user_items_path)

        # LLM service (initialized before HybridRecommender so it can be injected)
        app.state.llm_service = None
        if settings.llm_enabled:
            try:
                from cinematch.services.llm_service import LLMService

                llm_service = LLMService(
                    base_url=settings.llm_base_url,
                    model_name=settings.llm_model_name,
                    timeout=settings.llm_rerank_timeout,
                    backend=settings.llm_backend,
                    api_key=(
                        settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
                    ),
                )
                app.state.llm_service = llm_service
                logger.info(
                    "LLM service enabled (model=%s, backend=%s).",
                    settings.llm_model_name,
                    settings.llm_backend,
                )
            except Exception:
                logger.warning(
                    "Failed to initialize LLM service. "
                    "Recommendations will use algorithmic fallback."
                )
                app.state.llm_service = None

        # Create services
        content_recommender = ContentRecommender(embedding_service, faiss_index, faiss_id_map)
        collab_recommender = CollabRecommender(
            als_model, als_user_map, als_item_map, als_user_items
        )
        hybrid_recommender = HybridRecommender(
            content_recommender,
            collab_recommender,
            alpha=settings.hybrid_alpha,
            llm_service=app.state.llm_service,
            sequel_penalty=settings.hybrid_sequel_penalty,
            diversity_lambda=settings.hybrid_diversity_lambda,
            rerank_candidates=settings.llm_rerank_candidates,
            llm_rerank_enabled=settings.llm_rerank_enabled,
        )

        # Attach to app.state
        app.state.embedding_service = embedding_service
        app.state.content_recommender = content_recommender
        app.state.collab_recommender = collab_recommender
        app.state.hybrid_recommender = hybrid_recommender

        logger.info("All recommendation services loaded successfully.")
    except FileNotFoundError:
        logger.warning(
            "Data artifacts not found. Run the pipeline first. "
            "App will start without recommendation services."
        )

    # Services that work without pipeline artifacts
    app.state.movie_service = MovieService()
    app.state.rating_service = RatingService()
    app.state.user_stats_service = UserStatsService()
    app.state.watchlist_service = WatchlistService()
    app.state.dismissal_service = DismissalService()
    app.state.user_list_service = UserListService()
    app.state.thematic_collection_service = ThematicCollectionService(
        movie_service=app.state.movie_service,
    )
    app.state.rating_comparison_service = RatingComparisonService()
    app.state.streak_service = StreakService()
    app.state.taste_evolution_service = TasteEvolutionService()
    app.state.global_stats_service = GlobalStatsService()
    app.state.achievement_service = AchievementService()
    app.state.challenge_service = ChallengeService()
    app.state.bingo_service = BingoService()
    app.state.rewatch_service = RewatchService()
    app.state.blind_spot_service = BlindSpotService()
    app.state.onboarding_service = OnboardingService()
    app.state.taste_profile_service = TasteProfileService(
        user_stats_service=app.state.user_stats_service,
        llm_service=getattr(app.state, "llm_service", None),
    )

    # Inject dismissal service into hybrid recommender (created earlier in try block)
    hybrid = getattr(app.state, "hybrid_recommender", None)
    if hybrid is not None:
        hybrid._dismissal_service = app.state.dismissal_service

    # Feed service (works with or without recommendation artifacts)
    app.state.feed_service = FeedService(
        movie_service=app.state.movie_service,
        user_stats_service=app.state.user_stats_service,
        content_recommender=getattr(app.state, "content_recommender", None),
        collab_recommender=getattr(app.state, "collab_recommender", None),
        hybrid_recommender=getattr(app.state, "hybrid_recommender", None),
        dismissal_service=app.state.dismissal_service,
    )

    # Redis cache (optional — app works without it)
    try:
        cache_service = CacheService(
            redis_url=settings.redis_url.get_secret_value(), default_ttl=settings.cache_ttl_seconds
        )
        app.state.cache_service = cache_service
        logger.info("Redis cache connected.")
    except Exception:
        logger.warning("Redis not available. App will run without caching.")
        app.state.cache_service = None

    yield

    # Shutdown
    if getattr(app.state, "llm_service", None) is not None:
        await app.state.llm_service.close()
    if getattr(app.state, "cache_service", None) is not None:
        await app.state.cache_service.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="CineMatch-AI",
        description="Hybrid movie recommendation system",
        version=__version__,
        lifespan=lifespan,
    )

    app.state.limiter = limiter

    settings = get_settings()

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
    )

    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(ServiceUnavailableError, service_unavailable_handler)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_exception_handler(Exception, catch_all_handler)

    app.include_router(api_v1_router)

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
