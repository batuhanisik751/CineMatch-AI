"""Tests for LightweightHybridRecommender (pgvector + cached collab)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from cinematch.services.lightweight_collab_recommender import LightweightCollabRecommender
from cinematch.services.lightweight_content_recommender import LightweightContentRecommender
from cinematch.services.lightweight_hybrid_recommender import LightweightHybridRecommender

EMBEDDING_DIM = 384


def _make_normalized_vectors(n: int, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed)
    vecs = rng.randn(n, EMBEDDING_DIM).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / norms


@pytest.fixture()
def mock_lw_embedding_service():
    svc = MagicMock()
    vec = _make_normalized_vectors(1)[0]
    svc.embed_text.return_value = vec
    return svc


@pytest.fixture()
def mock_lw_content():
    content = AsyncMock(spec=LightweightContentRecommender)
    content.get_similar_movies.return_value = [
        (201, 0.95), (202, 0.90), (203, 0.85), (204, 0.80), (205, 0.75),
    ]
    content.pgvector_search_by_vector.return_value = [
        (201, 0.92), (202, 0.88), (203, 0.80),
    ]
    vecs = _make_normalized_vectors(5)
    content.fetch_embeddings.return_value = {
        201: vecs[0], 202: vecs[1], 203: vecs[2], 204: vecs[3], 205: vecs[4],
    }
    content._embedding_service = MagicMock()
    content._embedding_service.embed_text.return_value = _make_normalized_vectors(1)[0]
    return content


@pytest.fixture()
def mock_lw_collab():
    collab = AsyncMock(spec=LightweightCollabRecommender)
    collab.is_known_user.return_value = True
    collab.recommend_for_user.return_value = [
        (201, 0.9), (202, 0.8), (206, 0.7), (207, 0.6),
    ]
    collab.score_items.return_value = {201: 0.9, 202: 0.8, 203: 0.7}
    return collab


@pytest.fixture()
def mock_db():
    return AsyncMock()


@pytest.fixture()
def lw_hybrid(mock_lw_content, mock_lw_collab):
    return LightweightHybridRecommender(
        content_recommender=mock_lw_content,
        collab_recommender=mock_lw_collab,
        alpha=0.5,
        llm_service=None,
        sequel_penalty=0.5,
        diversity_lambda=0.7,
        rerank_candidates=50,
        llm_rerank_enabled=False,
    )


# ------------------------------------------------------------------
# recommend (collab strategy)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collab_only_recommend(lw_hybrid, mock_db):
    """Collab-only strategy reads from cache."""
    results = await lw_hybrid.recommend(user_id=1, db=mock_db, strategy="collab", top_k=3)
    assert len(results) > 0
    # All results should have collab_score in breakdown
    for r in results:
        assert r.score_breakdown is not None
        assert r.score_breakdown.alpha == 0.0


@pytest.mark.asyncio
async def test_collab_only_raises_for_unknown_user(lw_hybrid, mock_db, mock_lw_collab):
    """Collab-only raises ValueError for cold-start user."""
    mock_lw_collab.is_known_user.return_value = False
    with pytest.raises(ValueError, match="no collaborative filtering data"):
        await lw_hybrid.recommend(user_id=999, db=mock_db, strategy="collab")


# ------------------------------------------------------------------
# mood_recommend (pgvector instead of FAISS)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mood_recommend_cold_start(lw_hybrid, mock_db):
    """Cold-start user gets unpersonalized mood results."""
    # Mock _get_user_top_rated_diverse to return empty (cold start)
    lw_hybrid._get_user_top_rated_diverse = AsyncMock(return_value=[])
    lw_hybrid._get_excluded_movie_ids = AsyncMock(return_value=set())

    results, is_personalized = await lw_hybrid.mood_recommend(
        "feel-good comedies", user_id=999, db=mock_db, top_k=3
    )
    assert not is_personalized
    assert len(results) == 3


@pytest.mark.asyncio
async def test_mood_recommend_personalized(lw_hybrid, mock_db, mock_lw_content):
    """Known user gets personalized mood results with taste blending."""
    lw_hybrid._get_user_top_rated_diverse = AsyncMock(
        return_value=[(201, 9.0), (202, 8.0)]
    )
    lw_hybrid._get_excluded_movie_ids = AsyncMock(return_value=set())

    results, is_personalized = await lw_hybrid.mood_recommend(
        "dark thrillers", user_id=1, db=mock_db, top_k=3
    )
    assert is_personalized
    assert len(results) == 3
    # Should have called fetch_embeddings for the user's top movies
    mock_lw_content.fetch_embeddings.assert_called()


# ------------------------------------------------------------------
# watchlist_recommend (pgvector instead of FAISS)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watchlist_recommend(lw_hybrid, mock_db, mock_lw_content):
    """Watchlist recommendations use pgvector mean embedding search."""
    lw_hybrid._get_excluded_movie_ids = AsyncMock(return_value=set())

    results = await lw_hybrid.watchlist_recommend(
        watchlist_movie_ids=[201, 202], user_id=1, db=mock_db, top_k=3
    )
    assert len(results) == 3
    mock_lw_content.fetch_embeddings.assert_called_once_with([201, 202], mock_db)
    mock_lw_content.pgvector_search_by_vector.assert_called()


@pytest.mark.asyncio
async def test_watchlist_recommend_empty(lw_hybrid, mock_db):
    """Empty watchlist returns empty results."""
    results = await lw_hybrid.watchlist_recommend(
        watchlist_movie_ids=[], user_id=1, db=mock_db
    )
    assert results == []


# ------------------------------------------------------------------
# predict_match (pgvector + async collab)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_predict_match(lw_hybrid, mock_db, mock_lw_content, mock_lw_collab):
    """Predict match uses DB embeddings and cached collab scores."""
    lw_hybrid._get_user_top_rated_diverse = AsyncMock(
        return_value=[(201, 9.0), (202, 8.0)]
    )

    results = await lw_hybrid.predict_match(
        user_id=1, movie_ids=[201, 202, 203], db=mock_db
    )
    assert len(results) == 3
    for r in results:
        assert 0 <= r.match_percent <= 100
        assert r.alpha is not None


@pytest.mark.asyncio
async def test_predict_match_cold_start(lw_hybrid, mock_db):
    """Cold-start user gets empty predictions."""
    lw_hybrid._get_user_top_rated_diverse = AsyncMock(return_value=[])
    results = await lw_hybrid.predict_match(user_id=999, movie_ids=[201], db=mock_db)
    assert results == []


# ------------------------------------------------------------------
# from_seed_recommend (async collab)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_from_seed_recommend(lw_hybrid, mock_db, mock_lw_collab):
    """Seed-based recommend uses async collab lookups."""
    lw_hybrid._get_excluded_movie_ids = AsyncMock(return_value=set())
    lw_hybrid._get_movie_titles = AsyncMock(return_value={201: "Seed Movie"})
    lw_hybrid._get_movie_genres = AsyncMock(return_value={})
    lw_hybrid._generate_feature_explanations = AsyncMock(return_value={})

    await lw_hybrid.from_seed_recommend(
        seed_movie_id=101, user_id=1, db=mock_db, top_k=3
    )
    # Should have called async collab methods
    mock_lw_collab.is_known_user.assert_called()
    mock_lw_collab.score_items.assert_called()


# ------------------------------------------------------------------
# _compute_taste_centroid_async
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_taste_centroid_async(lw_hybrid, mock_db, mock_lw_content):
    """Taste centroid computed from DB embeddings is L2-normalized."""
    user_top = [(201, 9.0), (202, 8.0)]
    centroid = await lw_hybrid._compute_taste_centroid_async(user_top, mock_db)
    assert centroid is not None
    assert centroid.shape == (EMBEDDING_DIM,)
    norm = np.linalg.norm(centroid)
    assert abs(norm - 1.0) < 1e-5


@pytest.mark.asyncio
async def test_compute_taste_centroid_async_no_embeddings(lw_hybrid, mock_db, mock_lw_content):
    """Returns None when no embeddings found."""
    mock_lw_content.fetch_embeddings.return_value = {}
    centroid = await lw_hybrid._compute_taste_centroid_async([(999, 9.0)], mock_db)
    assert centroid is None
