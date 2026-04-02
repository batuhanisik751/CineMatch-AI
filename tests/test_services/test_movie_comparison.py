"""Tests for movie comparison service methods."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.movie_service import MovieService
from cinematch.services.rating_service import RatingService


@pytest.fixture()
def movie_service():
    return MovieService()


@pytest.fixture()
def rating_service():
    return RatingService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


@pytest.mark.asyncio
async def test_embedding_cosine_similarity_returns_float(movie_service, mock_db):
    row = MagicMock()
    row.__getitem__ = lambda self, idx: 0.8523
    result = MagicMock()
    result.first.return_value = row
    mock_db.execute.return_value = result

    sim = await movie_service.embedding_cosine_similarity(1, 2, mock_db)
    assert sim == 0.8523
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_embedding_cosine_similarity_returns_none_when_no_embedding(movie_service, mock_db):
    result = MagicMock()
    result.first.return_value = None
    mock_db.execute.return_value = result

    sim = await movie_service.embedding_cosine_similarity(1, 2, mock_db)
    assert sim is None


@pytest.mark.asyncio
async def test_get_rating_stats_pair_returns_stats(rating_service, mock_db):
    row1 = (1, 7.5, 100)
    row2 = (2, 6.3, 80)
    result = MagicMock()
    result.all.return_value = [row1, row2]
    mock_db.execute.return_value = result

    stats = await rating_service.get_rating_stats_pair(1, 2, mock_db)
    assert stats[1] == (7.5, 100)
    assert stats[2] == (6.3, 80)


@pytest.mark.asyncio
async def test_get_rating_stats_pair_returns_empty_when_no_ratings(rating_service, mock_db):
    result = MagicMock()
    result.all.return_value = []
    mock_db.execute.return_value = result

    stats = await rating_service.get_rating_stats_pair(1, 2, mock_db)
    assert stats == {}
