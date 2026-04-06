"""Tests for LightweightContentRecommender (pgvector only, no FAISS)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from cinematch.services.lightweight_content_recommender import LightweightContentRecommender

EMBEDDING_DIM = 384


@pytest.fixture()
def mock_lw_embedding_service():
    svc = MagicMock()
    rng = np.random.RandomState(42)
    svc.embed_text.return_value = rng.randn(EMBEDDING_DIM).astype(np.float32)
    return svc


@pytest.fixture()
def lw_content_recommender(mock_lw_embedding_service):
    return LightweightContentRecommender(mock_lw_embedding_service)


@pytest.fixture()
def mock_db():
    return AsyncMock()


# ------------------------------------------------------------------
# get_similar_movies
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_similar_movies_returns_results(lw_content_recommender, mock_db):
    """pgvector search returns movie_id + similarity tuples."""
    # Mock: first query returns the movie's embedding
    embedding_result = MagicMock()
    embedding_row = MagicMock()
    embedding_row.__getitem__ = lambda self, idx: [0.1] * 384 if idx == 0 else None
    embedding_result.first.return_value = embedding_row

    # Mock: second query returns similar movies
    similar_result = MagicMock()
    similar_result.fetchall.return_value = [(201, 0.95), (202, 0.88), (203, 0.72)]

    mock_db.execute.side_effect = [embedding_result, similar_result]

    results = await lw_content_recommender.get_similar_movies(101, mock_db, top_k=3)
    assert len(results) == 3
    assert results[0] == (201, 0.95)
    assert results[2] == (203, 0.72)


@pytest.mark.asyncio
async def test_get_similar_movies_empty_when_no_embedding(lw_content_recommender, mock_db):
    """Returns empty list when the movie has no embedding."""
    result = MagicMock()
    result.first.return_value = None
    mock_db.execute.return_value = result

    results = await lw_content_recommender.get_similar_movies(999, mock_db)
    assert results == []


# ------------------------------------------------------------------
# pgvector_search_by_vector
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pgvector_search_by_vector(lw_content_recommender, mock_db):
    """Vector search returns results, excluding specified IDs."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(301, 0.91), (302, 0.85)]
    mock_db.execute.return_value = mock_result

    query_vec = np.random.randn(384).astype(np.float32)
    results = await lw_content_recommender.pgvector_search_by_vector(
        query_vec, mock_db, top_k=5, exclude_ids={101, 102}
    )
    assert len(results) == 2
    assert results[0] == (301, 0.91)


@pytest.mark.asyncio
async def test_pgvector_search_by_vector_no_excludes(lw_content_recommender, mock_db):
    """Vector search works without exclude_ids."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(401, 0.99)]
    mock_db.execute.return_value = mock_result

    query_vec = np.random.randn(384).astype(np.float32)
    results = await lw_content_recommender.pgvector_search_by_vector(query_vec, mock_db, top_k=1)
    assert results == [(401, 0.99)]


# ------------------------------------------------------------------
# fetch_embeddings
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_embeddings(lw_content_recommender, mock_db):
    """Batch-fetch embeddings from the database."""
    vec1 = list(np.random.randn(384).astype(float))
    vec2 = list(np.random.randn(384).astype(float))
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(101, vec1), (102, vec2)]
    mock_db.execute.return_value = mock_result

    embeddings = await lw_content_recommender.fetch_embeddings([101, 102], mock_db)
    assert set(embeddings.keys()) == {101, 102}
    assert embeddings[101].shape == (384,)
    assert embeddings[101].dtype == np.float32


@pytest.mark.asyncio
async def test_fetch_embeddings_empty(lw_content_recommender, mock_db):
    """Returns empty dict for empty input."""
    result = await lw_content_recommender.fetch_embeddings([], mock_db)
    assert result == {}


# ------------------------------------------------------------------
# Stubs for safety
# ------------------------------------------------------------------


def test_faiss_stubs_are_none(lw_content_recommender):
    """FAISS attributes exist as stubs but are empty/None."""
    assert lw_content_recommender._faiss_index is None
    assert lw_content_recommender._faiss_id_map == []
    assert lw_content_recommender._id_to_faiss_idx == {}
