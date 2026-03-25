"""FastAPI application factory with lifespan events."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cinematch import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load models and services (implemented in later phases)
    yield
    # Shutdown: cleanup resources


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

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
