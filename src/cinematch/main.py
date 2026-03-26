"""FastAPI application factory with lifespan events."""

from __future__ import annotations

import logging
import pickle
from contextlib import asynccontextmanager

import faiss
import scipy.sparse as sp
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cinematch import __version__
from cinematch.api.v1.router import api_v1_router
from cinematch.config import get_settings
from cinematch.services.collab_recommender import CollabRecommender
from cinematch.services.content_recommender import ContentRecommender
from cinematch.services.embedding_service import EmbeddingService
from cinematch.services.hybrid_recommender import HybridRecommender
from cinematch.services.movie_service import MovieService
from cinematch.services.rating_service import RatingService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

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

        # Create services
        content_recommender = ContentRecommender(embedding_service, faiss_index, faiss_id_map)
        collab_recommender = CollabRecommender(
            als_model, als_user_map, als_item_map, als_user_items
        )
        hybrid_recommender = HybridRecommender(
            content_recommender, collab_recommender, alpha=settings.hybrid_alpha
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

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="CineMatch-AI",
        description="Hybrid movie recommendation system",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router)

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
