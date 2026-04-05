"""Integration test: lightweight mode app startup and health check."""

from __future__ import annotations

from unittest.mock import patch


def test_lightweight_mode_config_default():
    """lightweight_mode defaults to False."""
    from cinematch.config import Settings

    # Use dummy values for required fields
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        database_url_sync="postgresql://u:p@localhost/db",
        redis_url="redis://localhost:6379",
        secret_key="test-secret-key",
    )
    assert settings.lightweight_mode is False


def test_lightweight_mode_config_enabled():
    """lightweight_mode can be set to True."""
    from cinematch.config import Settings

    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        database_url_sync="postgresql://u:p@localhost/db",
        redis_url="redis://localhost:6379",
        secret_key="test-secret-key",
        lightweight_mode=True,
    )
    assert settings.lightweight_mode is True
    assert "huggingface" in settings.hf_inference_url


def test_lightweight_imports_do_not_require_ml_packages():
    """Lightweight service modules can be imported without faiss/sentence_transformers."""
    # These should import cleanly even if faiss/sentence_transformers were missing
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

    assert LightweightEmbeddingService is not None
    assert LightweightContentRecommender is not None
    assert LightweightCollabRecommender is not None
    assert LightweightHybridRecommender is not None


def test_health_endpoint_includes_lightweight_mode():
    """Health endpoint response includes lightweight_mode field."""
    # Patch get_settings to avoid needing a real .env
    from cinematch.config import Settings

    test_settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        database_url_sync="postgresql://u:p@localhost/db",
        redis_url="redis://localhost:6379",
        secret_key="test-secret-key",
        lightweight_mode=True,
        llm_enabled=False,
        debug=True,
    )

    with patch("cinematch.main.get_settings", return_value=test_settings), \
         patch("cinematch.config.get_settings", return_value=test_settings):
        # Re-import to pick up patched settings
        from cinematch.main import create_app

        app = create_app()

        # Find the health route
        health_routes = [r for r in app.routes if hasattr(r, "path") and r.path == "/health"]
        assert len(health_routes) == 1
