"""Tests for RatingService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.rating_service import RatingService


@pytest.fixture()
def service():
    return RatingService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


@pytest.mark.asyncio
async def test_bulk_check_returns_rated_movies(service, mock_db):
    """bulk_check returns {movie_id: rating} for rated movies."""
    result = MagicMock()
    result.all.return_value = [(1, 8), (3, 6)]
    mock_db.execute = AsyncMock(return_value=result)

    ratings = await service.bulk_check(1, [1, 2, 3, 4], mock_db)

    assert ratings == {1: 8, 3: 6}
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_check_empty_input(service, mock_db):
    """bulk_check with empty list returns empty dict without querying."""
    result = await service.bulk_check(1, [], mock_db)

    assert result == {}
    mock_db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_bulk_check_no_matches(service, mock_db):
    """bulk_check returns empty dict when user has not rated any of the given movies."""
    result = MagicMock()
    result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=result)

    ratings = await service.bulk_check(1, [10, 20, 30], mock_db)

    assert ratings == {}


@pytest.mark.asyncio
async def test_get_rated_movie_ids_returns_set(service, mock_db):
    """get_rated_movie_ids returns a set of movie IDs the user has rated."""
    result = MagicMock()
    result.fetchall.return_value = [(1,), (5,), (10,)]
    mock_db.execute = AsyncMock(return_value=result)

    ids = await service.get_rated_movie_ids(1, mock_db)

    assert ids == {1, 5, 10}
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_rated_movie_ids_empty(service, mock_db):
    """get_rated_movie_ids returns empty set when user has no ratings."""
    result = MagicMock()
    result.fetchall.return_value = []
    mock_db.execute = AsyncMock(return_value=result)

    ids = await service.get_rated_movie_ids(1, mock_db)

    assert ids == set()


@pytest.mark.asyncio
async def test_get_movie_activity_groups_by_month(service, mock_db):
    """get_movie_activity returns timeline grouped by month."""
    from datetime import UTC, datetime

    row1 = (datetime(2024, 1, 1, tzinfo=UTC), 15, 7.50)
    row2 = (datetime(2024, 2, 1, tzinfo=UTC), 22, 8.10)
    result = MagicMock()
    result.all.return_value = [row1, row2]
    mock_db.execute = AsyncMock(return_value=result)

    data = await service.get_movie_activity(1, "month", mock_db)

    assert data["movie_id"] == 1
    assert data["granularity"] == "month"
    assert len(data["timeline"]) == 2
    assert data["timeline"][0]["period"] == "2024-01"
    assert data["timeline"][0]["rating_count"] == 15
    assert data["timeline"][1]["avg_rating"] == 8.10
    assert data["total_ratings"] == 37


@pytest.mark.asyncio
async def test_get_movie_activity_empty(service, mock_db):
    """get_movie_activity returns empty timeline when no ratings exist."""
    result = MagicMock()
    result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=result)

    data = await service.get_movie_activity(1, "month", mock_db)

    assert data["timeline"] == []
    assert data["total_ratings"] == 0
