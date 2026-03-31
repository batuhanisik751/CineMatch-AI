"""Tests for MovieService.controversial method."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.movie_service import MovieService


def _mock_movie(id: int = 1, title: str = "Polarizing Film") -> MagicMock:
    m = MagicMock()
    m.id = id
    m.title = title
    return m


@pytest.fixture()
def service():
    return MovieService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


async def test_controversial_returns_ordered_by_stddev(service, mock_db):
    """Results are ordered by standard deviation descending."""
    movie_a = _mock_movie(id=1, title="Very Divisive")
    movie_b = _mock_movie(id=2, title="Somewhat Divisive")

    # Step 1: aggregate query returns two movies
    agg_result = MagicMock()
    agg_result.all.return_value = [
        (1, 6.0, 3.5, 200),  # movie_id, avg, stddev, count
        (2, 7.0, 2.8, 150),
    ]

    # Step 2: histogram query
    hist_result = MagicMock()
    hist_result.all.return_value = [
        (1, 1, 30),
        (1, 5, 40),
        (1, 10, 130),
        (2, 3, 50),
        (2, 7, 100),
    ]

    # Step 3: get_movies_by_ids query
    movies_result = MagicMock()
    movies_result.scalars.return_value.all.return_value = [movie_a, movie_b]

    mock_db.execute = AsyncMock(side_effect=[agg_result, hist_result, movies_result])

    results = await service.controversial(mock_db, min_ratings=100, limit=10)

    assert len(results) == 2
    # First result should be the one with higher stddev
    assert results[0][0].id == 1
    assert results[0][2] == 3.5  # stddev
    assert results[1][0].id == 2
    assert results[1][2] == 2.8


async def test_controversial_empty_result(service, mock_db):
    """Returns empty list when no movies meet the threshold."""
    agg_result = MagicMock()
    agg_result.all.return_value = []

    mock_db.execute = AsyncMock(return_value=agg_result)

    results = await service.controversial(mock_db, min_ratings=1000, limit=10)
    assert results == []


async def test_controversial_histogram_has_all_buckets(service, mock_db):
    """Histogram dict has keys 1-10 even when some ratings are missing."""
    movie = _mock_movie(id=1)

    agg_result = MagicMock()
    agg_result.all.return_value = [(1, 5.0, 3.0, 100)]

    # Only a few rating values present
    hist_result = MagicMock()
    hist_result.all.return_value = [(1, 1, 40), (1, 10, 60)]

    movies_result = MagicMock()
    movies_result.scalars.return_value.all.return_value = [movie]

    mock_db.execute = AsyncMock(side_effect=[agg_result, hist_result, movies_result])

    results = await service.controversial(mock_db, min_ratings=50, limit=10)

    assert len(results) == 1
    histogram = results[0][4]
    # All 10 buckets present
    assert set(histogram.keys()) == set(range(1, 11))
    # Missing ratings are 0
    assert histogram[1] == 40
    assert histogram[10] == 60
    assert histogram[5] == 0
