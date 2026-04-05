"""Tests for LightweightCollabRecommender (recommendations_cache table)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.lightweight_collab_recommender import LightweightCollabRecommender


@pytest.fixture()
def lw_collab():
    return LightweightCollabRecommender()


@pytest.fixture()
def mock_db():
    return AsyncMock()


# ------------------------------------------------------------------
# recommend_for_user
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommend_for_user_returns_cached_results(lw_collab, mock_db):
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(101, 0.95), (102, 0.88), (103, 0.72)]
    mock_db.execute.return_value = mock_result

    results = await lw_collab.recommend_for_user(user_id=1, db=mock_db, top_k=3)
    assert len(results) == 3
    assert results[0] == (101, 0.95)
    assert results[2] == (103, 0.72)


@pytest.mark.asyncio
async def test_recommend_for_user_empty_for_unknown_user(lw_collab, mock_db):
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    results = await lw_collab.recommend_for_user(user_id=999, db=mock_db)
    assert results == []


# ------------------------------------------------------------------
# score_items
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_items_returns_scores(lw_collab, mock_db):
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(101, 0.9), (103, 0.7)]
    mock_db.execute.return_value = mock_result

    scores = await lw_collab.score_items(user_id=1, movie_ids=[101, 102, 103], db=mock_db)
    assert scores == {101: 0.9, 103: 0.7}


@pytest.mark.asyncio
async def test_score_items_empty_input(lw_collab, mock_db):
    scores = await lw_collab.score_items(user_id=1, movie_ids=[], db=mock_db)
    assert scores == {}


# ------------------------------------------------------------------
# is_known_user
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_is_known_user_true(lw_collab, mock_db):
    mock_result = MagicMock()
    mock_result.scalar.return_value = True
    mock_db.execute.return_value = mock_result

    assert await lw_collab.is_known_user(user_id=1, db=mock_db) is True


@pytest.mark.asyncio
async def test_is_known_user_false(lw_collab, mock_db):
    mock_result = MagicMock()
    mock_result.scalar.return_value = False
    mock_db.execute.return_value = mock_result

    assert await lw_collab.is_known_user(user_id=999, db=mock_db) is False
