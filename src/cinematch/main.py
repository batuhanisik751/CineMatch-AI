"""FastAPI application factory with lifespan events."""

from __future__ import annotations

import logging
import pickle
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from cinematch import __version__
from cinematch.api.v1.router import api_v1_router
from cinematch.config import get_settings
from cinematch.core.audit_middleware import AuditMiddleware
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
from cinematch.core.pickle_safety import verify_and_log
from cinematch.core.rate_limit import limiter
from cinematch.services.achievement_service import AchievementService
from cinematch.services.bingo_service import BingoService
from cinematch.services.blind_spot_service import BlindSpotService
from cinematch.services.challenge_service import ChallengeService
from cinematch.services.dismissal_service import DismissalService
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


def _verify_or_abort(path: str) -> None:
    """Verify pickle checksum; abort on mismatch, warn on missing."""
    status = verify_and_log(path)
    if status == "mismatch":
        raise RuntimeError(
            f"Pickle integrity check FAILED for {path}. "
            "The file may have been tampered with. Aborting startup."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(debug=settings.debug)

    # LLM service (shared by both lightweight and full modes)
    app.state.llm_service = None
    if settings.llm_enabled:
        try:
            from cinematch.services.llm_service import LLMService

            llm_service = LLMService(
                base_url=settings.llm_base_url,
                model_name=settings.llm_model_name,
                timeout=settings.llm_rerank_timeout,
                backend=settings.llm_backend,
                api_key=(settings.llm_api_key.get_secret_value() if settings.llm_api_key else None),
            )
            app.state.llm_service = llm_service
            logger.info(
                "LLM service enabled (model=%s, backend=%s).",
                settings.llm_model_name,
                settings.llm_backend,
            )
        except Exception:
            logger.warning(
                "Failed to initialize LLM service. Recommendations will use algorithmic fallback."
            )
            app.state.llm_service = None

    if settings.lightweight_mode:
        # ---- LIGHTWEIGHT MODE: no ML models, use pgvector + HF API + cache ----
        logger.info("Starting in LIGHTWEIGHT mode (no ML models loaded)")
        from cinematch.services.lightweight_collab_recommender import (
            LightweightCollabRecommender,
        )
        from cinematch.services.lightweight_content_recommender import (
            LightweightContentRecommender,
        )
        from cinematch.services.lightweight_embedding_service import (
            LightweightEmbeddingService,
        )
        from cinematch.services.lightweight_hybrid_recommender import (
            LightweightHybridRecommender,
        )

        embedding_service = LightweightEmbeddingService(
            inference_url=settings.hf_inference_url,
            api_token=(settings.hf_api_token.get_secret_value() if settings.hf_api_token else None),
        )
        await embedding_service.warm_up()

        content_recommender = LightweightContentRecommender(embedding_service)
        collab_recommender = LightweightCollabRecommender()
        hybrid_recommender = LightweightHybridRecommender(
            content_recommender,
            collab_recommender,
            alpha=settings.hybrid_alpha,
            llm_service=app.state.llm_service,
            sequel_penalty=settings.hybrid_sequel_penalty,
            diversity_lambda=settings.hybrid_diversity_lambda,
            rerank_candidates=settings.llm_rerank_candidates,
            llm_rerank_enabled=settings.llm_rerank_enabled,
        )

        app.state.embedding_service = embedding_service
        app.state.content_recommender = content_recommender
        app.state.collab_recommender = collab_recommender
        app.state.hybrid_recommender = hybrid_recommender

        logger.info("Lightweight recommendation services loaded successfully.")
    else:
        # ---- FULL MODE: load ML models from disk ----
        try:
            import faiss
            import scipy.sparse as sp

            from cinematch.services.collab_recommender import CollabRecommender
            from cinematch.services.content_recommender import ContentRecommender
            from cinematch.services.embedding_service import EmbeddingService

            # Load embedding service
            logger.info("Loading embedding model: %s", settings.embedding_model_name)
            embedding_service = EmbeddingService(
                model_name=settings.embedding_model_name,
                batch_size=settings.embedding_batch_size,
            )

            # Load FAISS artifacts
            logger.info("Loading FAISS index from %s", settings.faiss_index_path)
            faiss_index = faiss.read_index(settings.faiss_index_path)
            _verify_or_abort(settings.faiss_id_map_path)
            with open(settings.faiss_id_map_path, "rb") as f:
                faiss_id_map = pickle.load(f)  # noqa: S301  # nosec B301 - trusted local artifact

            # Load ALS artifacts
            logger.info("Loading ALS model from %s", settings.als_model_path)
            for pkl_path in (
                settings.als_model_path,
                settings.als_user_map_path,
                settings.als_item_map_path,
            ):
                _verify_or_abort(pkl_path)
            with open(settings.als_model_path, "rb") as f:
                als_model = pickle.load(f)  # noqa: S301  # nosec B301 - trusted local artifact
            with open(settings.als_user_map_path, "rb") as f:
                als_user_map = pickle.load(f)  # noqa: S301  # nosec B301 - trusted local artifact
            with open(settings.als_item_map_path, "rb") as f:
                als_item_map = pickle.load(f)  # noqa: S301  # nosec B301 - trusted local artifact
            als_user_items = sp.load_npz(settings.als_user_items_path)

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

    # Audit logging service
    from cinematch.services.audit_service import AuditService

    app.state.audit_service = AuditService(
        log_file=settings.audit_log_file,
        enabled=settings.audit_log_enabled,
    )
    logger.info("Audit logging %s.", "enabled" if settings.audit_log_enabled else "disabled")

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
    embedding_svc = getattr(app.state, "embedding_service", None)
    if embedding_svc is not None and hasattr(embedding_svc, "close"):
        import asyncio

        result = embedding_svc.close()
        if asyncio.iscoroutine(result):
            await result


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="CineMatch-AI",
        description="Hybrid movie recommendation system",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
    )

    app.state.limiter = limiter

    app.add_middleware(AuditMiddleware)
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
        return {
            "status": "ok",
            "version": __version__,
            "debug": settings.debug,
            "lightweight_mode": settings.lightweight_mode,
        }

    if settings.debug:

        @app.get("/debug-embed")
        async def debug_embed():
            """Temporary debug endpoint to test embedding service."""
            svc = getattr(app.state, "embedding_service", None)
            if svc is None:
                return {"error": "embedding_service is None"}
            try:
                result = svc.embed_text("test")
                import asyncio

                if asyncio.iscoroutine(result):
                    result = await result
                return {
                    "ok": True,
                    "shape": list(result.shape),
                    "first_5": result[:5].tolist(),
                }
            except Exception as exc:
                return {"error": f"{type(exc).__name__}: {exc}"}

    return app


app = create_app()
