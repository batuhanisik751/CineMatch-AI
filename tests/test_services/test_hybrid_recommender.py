"""Tests for HybridRecommender."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cinematch.services.hybrid_recommender import HybridRecommender


@pytest.mark.asyncio
async def test_hybrid_recommend_combines_scores(hybrid_recommender, mock_db_session):
    """Hybrid should use both content and collab scores."""
    # Mock _get_user_top_rated -> user has rated movie 101 highly
    top_rated_result = MagicMock()
    top_rated_result.fetchall.return_value = [(101, 5.0)]

    # Mock _get_user_rated_movie_ids -> only 101
    rated_ids_result = MagicMock()
    rated_ids_result.fetchall.return_value = [(101,)]

    mock_db_session.execute = AsyncMock(side_effect=[top_rated_result, rated_ids_result])

    # Mock content recommender to return known results
    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]

        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="hybrid"
        )

    assert len(results) > 0
    # Results should not include the rated movie 101
    result_ids = [mid for mid, _ in results]
    assert 101 not in result_ids


@pytest.mark.asyncio
async def test_hybrid_recommend_cold_start_uses_content_only(hybrid_recommender, mock_db_session):
    """Cold-start user (unknown to ALS) should get content-only recs."""
    top_rated_result = MagicMock()
    top_rated_result.fetchall.return_value = [(101, 4.5)]
    rated_ids_result = MagicMock()
    rated_ids_result.fetchall.return_value = [(101,)]

    mock_db_session.execute = AsyncMock(side_effect=[top_rated_result, rated_ids_result])

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.85), (103, 0.75)]

        results = await hybrid_recommender.recommend(
            user_id=999, db=mock_db_session, top_k=5, strategy="hybrid"
        )

    assert len(results) > 0


@pytest.mark.asyncio
async def test_hybrid_recommend_excludes_already_rated(hybrid_recommender, mock_db_session):
    top_rated_result = MagicMock()
    top_rated_result.fetchall.return_value = [(101, 5.0), (102, 4.0)]
    rated_ids_result = MagicMock()
    rated_ids_result.fetchall.return_value = [(101,), (102,)]

    mock_db_session.execute = AsyncMock(side_effect=[top_rated_result, rated_ids_result])

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(101, 0.99), (103, 0.8), (104, 0.7)]

        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="hybrid"
        )

    result_ids = [mid for mid, _ in results]
    assert 101 not in result_ids
    assert 102 not in result_ids


@pytest.mark.asyncio
async def test_content_only_strategy(hybrid_recommender, mock_db_session):
    top_rated_result = MagicMock()
    top_rated_result.fetchall.return_value = [(101, 5.0)]
    rated_ids_result = MagicMock()
    rated_ids_result.fetchall.return_value = [(101,)]

    mock_db_session.execute = AsyncMock(side_effect=[top_rated_result, rated_ids_result])

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8)]

        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="content"
        )

    assert len(results) > 0


@pytest.mark.asyncio
async def test_collab_only_strategy(hybrid_recommender, mock_db_session):
    results = await hybrid_recommender.recommend(
        user_id=1, db=mock_db_session, top_k=3, strategy="collab"
    )
    assert len(results) == 3
    # Should be the mock ALS output: movie IDs [101, 103, 105]
    result_ids = [mid for mid, _ in results]
    assert result_ids == [101, 103, 105]


@pytest.mark.asyncio
async def test_invalid_strategy_raises_value_error(hybrid_recommender, mock_db_session):
    with pytest.raises(ValueError, match="Unknown strategy"):
        await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=5, strategy="invalid"
        )


def test_min_max_normalize_standard_case():
    scores = {1: 0.2, 2: 0.8, 3: 0.5}
    normed = HybridRecommender._min_max_normalize(scores)
    assert normed[1] == pytest.approx(0.0)
    assert normed[2] == pytest.approx(1.0)
    assert normed[3] == pytest.approx(0.5)


def test_min_max_normalize_all_equal_returns_half():
    scores = {1: 0.5, 2: 0.5, 3: 0.5}
    normed = HybridRecommender._min_max_normalize(scores)
    assert all(v == 0.5 for v in normed.values())


def test_min_max_normalize_empty_dict():
    assert HybridRecommender._min_max_normalize({}) == {}


def test_min_max_normalize_single_value():
    scores = {1: 0.7}
    normed = HybridRecommender._min_max_normalize(scores)
    assert normed[1] == 0.5


@pytest.mark.asyncio
async def test_recommend_user_with_no_ratings_returns_empty(hybrid_recommender, mock_db_session):
    """User with no ratings and unknown to ALS gets empty results."""
    top_rated_result = MagicMock()
    top_rated_result.fetchall.return_value = []
    rated_ids_result = MagicMock()
    rated_ids_result.fetchall.return_value = []

    mock_db_session.execute = AsyncMock(side_effect=[top_rated_result, rated_ids_result])

    results = await hybrid_recommender.recommend(
        user_id=999, db=mock_db_session, top_k=5, strategy="hybrid"
    )
    assert results == []


@pytest.mark.asyncio
async def test_hybrid_recommend_respects_top_k(hybrid_recommender, mock_db_session):
    top_rated_result = MagicMock()
    top_rated_result.fetchall.return_value = [(101, 5.0)]
    rated_ids_result = MagicMock()
    rated_ids_result.fetchall.return_value = [(101,)]

    mock_db_session.execute = AsyncMock(side_effect=[top_rated_result, rated_ids_result])

    with patch.object(
        hybrid_recommender._content, "get_similar_movies", new_callable=AsyncMock
    ) as mock_content:
        mock_content.return_value = [(102, 0.9), (103, 0.8), (104, 0.7), (105, 0.6)]

        results = await hybrid_recommender.recommend(
            user_id=1, db=mock_db_session, top_k=2, strategy="hybrid"
        )

    assert len(results) <= 2
