"""Tests for RatingComparisonService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.rating_comparison_service import RatingComparisonService


def _make_row(movie_id, title, poster_path, user_rating, community_avg):
    """Create a mock row matching the SQL query output."""
    row = MagicMock()
    row.movie_id = movie_id
    row.title = title
    row.poster_path = poster_path
    row.user_rating = user_rating
    row.community_avg = community_avg
    return row


@pytest.fixture()
def service():
    return RatingComparisonService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


@pytest.mark.asyncio
async def test_happy_path(service, mock_db):
    """Standard case with multiple rated movies."""
    rows = [
        _make_row(1, "Movie A", "/a.jpg", 9, 6.0),  # overrated +3.0
        _make_row(2, "Movie B", "/b.jpg", 7, 7.0),  # agrees 0.0
        _make_row(3, "Movie C", "/c.jpg", 3, 7.0),  # underrated -4.0
        _make_row(4, "Movie D", "/d.jpg", 8, 7.5),  # agrees +0.5
        _make_row(5, "Movie E", "/e.jpg", 5, 8.0),  # underrated -3.0
    ]
    result_mock = MagicMock()
    result_mock.all.return_value = rows
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_rating_comparison(1, mock_db)

    assert result["user_id"] == 1
    assert result["total_rated"] == 5
    assert result["user_avg"] == 6.4  # (9+7+3+8+5)/5
    assert result["community_avg"] == 7.1  # (6+7+7+7.5+8)/5
    # Agreements: Movie B (0.0), Movie D (0.5) = 2/5 = 40%
    assert result["agreement_pct"] == 40.0
    # Most overrated: Movie A (+3.0) first
    assert result["most_overrated"][0]["movie_id"] == 1
    assert result["most_overrated"][0]["difference"] == 3.0
    # Most underrated: Movie C (-4.0) first (reversed)
    assert result["most_underrated"][0]["movie_id"] == 3
    assert result["most_underrated"][0]["difference"] == -4.0


@pytest.mark.asyncio
async def test_no_ratings(service, mock_db):
    """User with no ratings returns zeroed response."""
    result_mock = MagicMock()
    result_mock.all.return_value = []
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_rating_comparison(99, mock_db)

    assert result["user_id"] == 99
    assert result["total_rated"] == 0
    assert result["user_avg"] == 0.0
    assert result["community_avg"] == 0.0
    assert result["agreement_pct"] == 0.0
    assert result["most_overrated"] == []
    assert result["most_underrated"] == []


@pytest.mark.asyncio
async def test_perfect_agreement(service, mock_db):
    """All ratings within 1.5 of community avg yields 100% agreement."""
    rows = [
        _make_row(1, "A", None, 7, 6.0),  # diff 1.0
        _make_row(2, "B", None, 8, 7.5),  # diff 0.5
        _make_row(3, "C", None, 5, 5.5),  # diff -0.5
    ]
    result_mock = MagicMock()
    result_mock.all.return_value = rows
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_rating_comparison(1, mock_db)

    assert result["agreement_pct"] == 100.0


@pytest.mark.asyncio
async def test_total_disagreement(service, mock_db):
    """All ratings differ by more than 1.5 yields 0% agreement."""
    rows = [
        _make_row(1, "A", None, 10, 5.0),  # diff 5.0
        _make_row(2, "B", None, 1, 8.0),  # diff -7.0
    ]
    result_mock = MagicMock()
    result_mock.all.return_value = rows
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_rating_comparison(1, mock_db)

    assert result["agreement_pct"] == 0.0


@pytest.mark.asyncio
async def test_single_rating(service, mock_db):
    """Edge case with exactly one rated movie."""
    rows = [_make_row(42, "Solo Movie", "/solo.jpg", 8, 6.5)]
    result_mock = MagicMock()
    result_mock.all.return_value = rows
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_rating_comparison(1, mock_db)

    assert result["total_rated"] == 1
    assert result["user_avg"] == 8.0
    assert result["community_avg"] == 6.5
    assert len(result["most_overrated"]) == 1
    assert len(result["most_underrated"]) == 1
    assert result["most_overrated"][0]["movie_id"] == 42
