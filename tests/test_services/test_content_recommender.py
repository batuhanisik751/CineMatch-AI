"""Tests for ContentRecommender."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from tests.test_services.conftest import SAMPLE_MOVIE_IDS, _make_normalized_vectors


@pytest.mark.asyncio
async def test_faiss_search_returns_similar_movies(content_recommender):
    results = content_recommender._faiss_search(movie_id=101, top_k=3)
    assert len(results) <= 3
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)


@pytest.mark.asyncio
async def test_faiss_search_excludes_query_movie(content_recommender):
    results = content_recommender._faiss_search(movie_id=101, top_k=5)
    result_ids = [mid for mid, _ in results]
    assert 101 not in result_ids


@pytest.mark.asyncio
async def test_faiss_search_unknown_movie_returns_empty(content_recommender):
    results = content_recommender._faiss_search(movie_id=999, top_k=5)
    assert results == []


@pytest.mark.asyncio
async def test_faiss_search_respects_top_k(content_recommender):
    results = content_recommender._faiss_search(movie_id=101, top_k=2)
    assert len(results) <= 2


@pytest.mark.asyncio
async def test_pgvector_search_returns_similar_movies(content_recommender, mock_db_session):
    # Mock the two DB queries: first fetches embedding, second fetches similar
    embeddings = _make_normalized_vectors(1)

    # First call: SELECT embedding FROM movies WHERE id = :movie_id
    first_result = MagicMock()
    first_result.first.return_value = (embeddings[0].tolist(),)

    # Second call: SELECT id, similarity FROM movies ORDER BY ...
    second_result = MagicMock()
    second_result.fetchall.return_value = [(102, 0.95), (103, 0.88)]

    mock_db_session.execute = AsyncMock(side_effect=[first_result, second_result])

    results = await content_recommender._pgvector_search(movie_id=101, db=mock_db_session, top_k=5)
    assert len(results) == 2
    assert results[0] == (102, 0.95)
    assert results[1] == (103, 0.88)


@pytest.mark.asyncio
async def test_pgvector_search_uses_typed_vector_binding(content_recommender, mock_db_session):
    """Verify query_embedding is passed as list, not str (pgvector type safety)."""
    embeddings = _make_normalized_vectors(1)

    first_result = MagicMock()
    first_result.first.return_value = (embeddings[0].tolist(),)

    second_result = MagicMock()
    second_result.fetchall.return_value = [(102, 0.95)]

    mock_db_session.execute = AsyncMock(side_effect=[first_result, second_result])

    await content_recommender._pgvector_search(movie_id=101, db=mock_db_session, top_k=5)

    # The second execute call is the similarity query
    second_call = mock_db_session.execute.call_args_list[1]
    params = second_call[0][1] if len(second_call[0]) > 1 else second_call.kwargs
    assert not isinstance(params["query_embedding"], str)


@pytest.mark.asyncio
async def test_pgvector_search_no_embedding_returns_empty(content_recommender, mock_db_session):
    first_result = MagicMock()
    first_result.first.return_value = None
    mock_db_session.execute = AsyncMock(return_value=first_result)

    results = await content_recommender._pgvector_search(movie_id=101, db=mock_db_session, top_k=5)
    assert results == []


@pytest.mark.asyncio
async def test_get_similar_movies_defaults_to_pgvector(content_recommender, mock_db_session):
    embeddings = _make_normalized_vectors(1)

    first_result = MagicMock()
    first_result.first.return_value = (embeddings[0].tolist(),)
    second_result = MagicMock()
    second_result.fetchall.return_value = [(102, 0.9)]
    mock_db_session.execute = AsyncMock(side_effect=[first_result, second_result])

    results = await content_recommender.get_similar_movies(
        movie_id=101, db=mock_db_session, top_k=5
    )
    assert len(results) == 1
    assert results[0][0] == 102


@pytest.mark.asyncio
async def test_get_similar_movies_falls_back_to_faiss(content_recommender, mock_db_session):
    mock_db_session.execute = AsyncMock(side_effect=Exception("DB error"))

    results = await content_recommender.get_similar_movies(
        movie_id=101, db=mock_db_session, top_k=3
    )
    # Should fall back to FAISS and return results
    assert len(results) > 0
    assert 101 not in [mid for mid, _ in results]


@pytest.mark.asyncio
async def test_get_similar_movies_faiss_when_pgvector_disabled(
    content_recommender, mock_db_session
):
    results = await content_recommender.get_similar_movies(
        movie_id=101, db=mock_db_session, top_k=3, use_pgvector=False
    )
    assert len(results) > 0


# ----- faiss_search_by_vector tests -----


def test_faiss_search_by_vector_returns_results(content_recommender, sample_embeddings):
    """Searching with a known vector returns movie IDs and scores."""
    query_vec = sample_embeddings[0]  # vector for movie 101
    results = content_recommender.faiss_search_by_vector(query_vec, top_k=3)
    assert len(results) > 0
    assert len(results) <= 3
    for mid, score in results:
        assert mid in SAMPLE_MOVIE_IDS
        assert isinstance(score, float)


def test_faiss_search_by_vector_excludes_ids(content_recommender, sample_embeddings):
    """Excluded movie IDs should not appear in results."""
    query_vec = sample_embeddings[0]
    exclude = {102, 103}
    results = content_recommender.faiss_search_by_vector(query_vec, top_k=5, exclude_ids=exclude)
    result_ids = {mid for mid, _ in results}
    assert result_ids.isdisjoint(exclude)


def test_faiss_search_by_vector_respects_top_k(content_recommender, sample_embeddings):
    """Results should not exceed top_k."""
    query_vec = sample_embeddings[0]
    results = content_recommender.faiss_search_by_vector(query_vec, top_k=2)
    assert len(results) <= 2


def test_faiss_search_by_vector_with_random_vector(content_recommender):
    """An arbitrary normalized vector should still return valid results."""
    rng = np.random.RandomState(99)
    vec = rng.randn(384).astype(np.float32)
    vec = vec / np.linalg.norm(vec)
    results = content_recommender.faiss_search_by_vector(vec, top_k=3)
    assert len(results) > 0
    for mid, score in results:
        assert mid in SAMPLE_MOVIE_IDS
