"""Tests for EmbeddingService."""

from __future__ import annotations

import numpy as np
import pandas as pd

from cinematch.services.embedding_service import EmbeddingService


def test_embed_text_returns_384_dim_vector(embedding_service):
    vec = embedding_service.embed_text("A sci-fi movie")
    assert vec.shape == (384,)


def test_embed_text_returns_float32(embedding_service):
    vec = embedding_service.embed_text("test")
    assert vec.dtype == np.float32


def test_embed_text_is_normalized(embedding_service):
    vec = embedding_service.embed_text("test")
    norm = float(np.linalg.norm(vec))
    assert abs(norm - 1.0) < 1e-5


def test_embed_batch_returns_correct_shape(embedding_service):
    texts = ["Movie A", "Movie B", "Movie C"]
    vecs = embedding_service.embed_batch(texts)
    assert vecs.shape == (3, 384)


def test_embed_batch_calls_encode_with_normalize(embedding_service):
    embedding_service.embed_batch(["a", "b"])
    call_kwargs = embedding_service._model.encode.call_args[1]
    assert call_kwargs["normalize_embeddings"] is True


def test_build_movie_text_full_fields():
    text = EmbeddingService.build_movie_text(
        title="The Matrix",
        overview="A computer hacker discovers reality is a simulation.",
        genres=["Action", "Sci-Fi"],
        keywords=["hacker", "simulation"],
    )
    assert text == (
        "The Matrix. A computer hacker discovers reality is a simulation. "
        "Genres: Action, Sci-Fi. Keywords: hacker, simulation."
    )


def test_build_movie_text_missing_overview():
    text = EmbeddingService.build_movie_text(
        title="The Matrix",
        overview=None,
        genres=["Action"],
        keywords=["hacker"],
    )
    assert "The Matrix." in text
    assert "Genres: Action." in text
    # No overview text between title and genres
    assert text == "The Matrix. Genres: Action. Keywords: hacker."


def test_build_movie_text_empty_genres():
    text = EmbeddingService.build_movie_text(
        title="Test",
        overview="An overview.",
        genres=[],
        keywords=["key"],
    )
    assert "Genres:" not in text


def test_build_movie_text_empty_keywords():
    text = EmbeddingService.build_movie_text(
        title="Test",
        overview="An overview.",
        genres=["Drama"],
        keywords=[],
    )
    assert "Keywords:" not in text


def test_build_movie_text_only_title():
    text = EmbeddingService.build_movie_text(title="Standalone")
    assert text == "Standalone."


def test_build_movie_text_matches_pipeline_format():
    """Verify service build_movie_text matches pipeline/embedder.py output."""
    from cinematch.pipeline.embedder import build_movie_text as pipeline_build

    row = pd.Series(
        {
            "title": "The Matrix",
            "overview": "A computer hacker discovers reality is a simulation.",
            "genres": ["Action", "Sci-Fi"],
            "keywords": ["hacker", "simulation"],
        }
    )
    pipeline_text = pipeline_build(row)

    service_text = EmbeddingService.build_movie_text(
        title="The Matrix",
        overview="A computer hacker discovers reality is a simulation.",
        genres=["Action", "Sci-Fi"],
        keywords=["hacker", "simulation"],
    )
    assert service_text == pipeline_text
