"""Tests for RatingService.get_movie_rating_stats."""

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


def _agg_row(avg, median, count, stddev=None):
    row = MagicMock()
    row.__getitem__ = lambda self, i: [avg, median, count, stddev][i]
    return row


def _dist_rows(counts: dict[int, int]):
    rows = []
    for rating, count in counts.items():
        r = MagicMock()
        r.__getitem__ = lambda self, i, _r=rating, _c=count: [_r, _c][i]
        rows.append(r)
    return rows


def _user_row(rating):
    r = MagicMock()
    r.__getitem__ = lambda self, i, _rating=rating: [_rating][i]
    return r


@pytest.mark.asyncio
async def test_basic_stats(service, mock_db):
    agg = MagicMock()
    agg.one.return_value = _agg_row(7.5, 8.0, 100, 1.58)

    dist = MagicMock()
    dist.all.return_value = _dist_rows({7: 30, 8: 40, 9: 20, 10: 10})

    mock_db.execute = AsyncMock(side_effect=[agg, dist])

    result = await service.get_movie_rating_stats(42, mock_db)

    assert result["movie_id"] == 42
    assert result["avg_rating"] == 7.5
    assert result["median_rating"] == 8.0
    assert result["total_ratings"] == 100
    assert result["stddev"] == 1.58
    assert result["polarization_score"] == 0.35
    assert len(result["distribution"]) == 10
    assert result["distribution"][6] == {"rating": 7, "count": 30}
    assert result["distribution"][0] == {"rating": 1, "count": 0}
    assert result["user_rating"] is None


@pytest.mark.asyncio
async def test_no_ratings(service, mock_db):
    agg = MagicMock()
    agg.one.return_value = _agg_row(None, None, 0, None)

    dist = MagicMock()
    dist.all.return_value = []

    mock_db.execute = AsyncMock(side_effect=[agg, dist])

    result = await service.get_movie_rating_stats(99, mock_db)

    assert result["avg_rating"] == 0.0
    assert result["median_rating"] == 0.0
    assert result["total_ratings"] == 0
    assert result["stddev"] == 0.0
    assert result["polarization_score"] == 0.0
    assert all(b["count"] == 0 for b in result["distribution"])
    assert result["user_rating"] is None


@pytest.mark.asyncio
async def test_with_user_rating(service, mock_db):
    agg = MagicMock()
    agg.one.return_value = _agg_row(6.0, 6.0, 50, 0.82)

    dist = MagicMock()
    dist.all.return_value = _dist_rows({5: 20, 6: 15, 7: 15})

    user_r = MagicMock()
    user_r.one_or_none.return_value = _user_row(8)

    mock_db.execute = AsyncMock(side_effect=[agg, dist, user_r])

    result = await service.get_movie_rating_stats(1, mock_db, user_id=42)

    assert result["user_rating"] == 8


@pytest.mark.asyncio
async def test_user_not_rated(service, mock_db):
    agg = MagicMock()
    agg.one.return_value = _agg_row(7.0, 7.0, 30, 1.0)

    dist = MagicMock()
    dist.all.return_value = _dist_rows({7: 30})

    user_r = MagicMock()
    user_r.one_or_none.return_value = None

    mock_db.execute = AsyncMock(side_effect=[agg, dist, user_r])

    result = await service.get_movie_rating_stats(1, mock_db, user_id=99)

    assert result["user_rating"] is None
