"""Tests for HybridRecommender.predict_match."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.hybrid_recommender import HybridRecommender, PredictedMatchResult


def _db_execute_factory(
    top_rated: list[tuple] | None = None,
    rated_ids: list[tuple] | None = None,
):
    """Build a query-matching side_effect for mock db.execute."""
    if top_rated is None:
        top_rated = [(101, 9.0, ["Action", "Sci-Fi"])]
    if rated_ids is None:
        rated_ids = [(101,)]

    def _make_result(data):
        r = MagicMock()
        r.fetchall.return_value = data
        return r

    async def _side_effect(query, params=None):
        q = str(query)
        if "r.movie_id, r.rating, m.genres" in q:
            return _make_result(top_rated)
        if "SELECT movie_id FROM ratings" in q:
            return _make_result(rated_ids)
        return _make_result([])

    return _side_effect


@pytest.mark.asyncio
async def test_predict_match_happy_path(hybrid_recommender, mock_db_session):
    """Hybrid user gets blended scores in [0, 100]."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    results = await hybrid_recommender.predict_match(1, [102, 103], mock_db_session)

    assert len(results) == 2
    for r in results:
        assert isinstance(r, PredictedMatchResult)
        assert 0 <= r.match_percent <= 100
        assert 0.0 <= r.content_score <= 1.0
        assert 0.0 <= r.collab_score <= 1.0
        assert r.alpha == 0.5  # Known user, default alpha


@pytest.mark.asyncio
async def test_predict_match_cold_start_user(
    content_recommender, collab_recommender, mock_db_session
):
    """Cold-start user (not in ALS) gets content-only scores (alpha=1.0)."""
    rec = HybridRecommender(content_recommender, collab_recommender, alpha=0.5)
    mock_db_session.execute = AsyncMock(
        side_effect=_db_execute_factory(
            top_rated=[(101, 8.0, ["Drama"])],
        )
    )

    # user_id=999 is not in the ALS user_map
    results = await rec.predict_match(999, [102, 103], mock_db_session)

    assert len(results) == 2
    for r in results:
        assert r.alpha == 1.0
        assert r.collab_score == 0.0  # No collab data
        assert 0 <= r.match_percent <= 100


@pytest.mark.asyncio
async def test_predict_match_no_ratings(hybrid_recommender, mock_db_session):
    """User with no ratings returns empty list."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory(top_rated=[], rated_ids=[]))

    results = await hybrid_recommender.predict_match(1, [102], mock_db_session)

    assert results == []


@pytest.mark.asyncio
async def test_predict_match_movie_not_in_faiss(hybrid_recommender, mock_db_session):
    """Movie not in FAISS gets content_score=0."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    # 999 is not in SAMPLE_MOVIE_IDS
    results = await hybrid_recommender.predict_match(1, [999], mock_db_session)

    assert len(results) == 1
    assert results[0].content_score == 0.0
    assert 0 <= results[0].match_percent <= 100


@pytest.mark.asyncio
async def test_predict_match_movie_not_in_als(hybrid_recommender, mock_db_session):
    """Movie not in ALS item map gets collab_score via sigmoid(0) = 0.5... actually 0."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    # 999 is not in sample_item_map but user 1 is known
    results = await hybrid_recommender.predict_match(1, [999], mock_db_session)

    assert len(results) == 1
    # collab_score should be 0.0 (movie not in ALS item map, score_items won't include it)
    assert results[0].collab_score == 0.0


@pytest.mark.asyncio
async def test_predict_match_batch_consistency(hybrid_recommender, mock_db_session):
    """Multi-movie call produces same results as individual calls."""
    mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())

    batch_results = await hybrid_recommender.predict_match(1, [102, 103, 104], mock_db_session)

    individual_results = []
    for mid in [102, 103, 104]:
        mock_db_session.execute = AsyncMock(side_effect=_db_execute_factory())
        r = await hybrid_recommender.predict_match(1, [mid], mock_db_session)
        individual_results.extend(r)

    batch_by_id = {r.movie_id: r.match_percent for r in batch_results}
    for r in individual_results:
        assert batch_by_id[r.movie_id] == r.match_percent
