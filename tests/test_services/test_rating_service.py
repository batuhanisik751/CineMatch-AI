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
