"""Tests for ChallengeService."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.challenge_service import ChallengeService, _week_boundaries, _week_key


@pytest.fixture()
def service():
    return ChallengeService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


def _pool_results(
    genres: list[str] | None = None,
    decades: list[int] | None = None,
    directors: list[tuple[str, int]] | None = None,
):
    """Return mock execute results for the 3 parameter pool queries."""
    genres = genres or ["Action", "Comedy", "Drama", "Horror", "Sci-Fi"]
    decades = decades or [1980, 1990, 2000, 2010, 2020]
    directors = directors or [
        ("Christopher Nolan", 10),
        ("Martin Scorsese", 25),
        ("Steven Spielberg", 30),
    ]

    genre_result = MagicMock()
    genre_result.all.return_value = [(g,) for g in genres]

    decade_result = MagicMock()
    decade_result.all.return_value = [(d,) for d in decades]

    director_result = MagicMock()
    director_result.all.return_value = [(n, c) for n, c in directors]

    return [genre_result, decade_result, director_result]


def _progress_result(movie_ids: list[int]):
    """Return a mock execute result for a progress query."""
    result = MagicMock()
    result.all.return_value = [(mid,) for mid in movie_ids]
    return result


@pytest.mark.asyncio
async def test_deterministic_generation(service, mock_db):
    """Same date produces identical challenges."""
    mock_db.execute = AsyncMock(side_effect=_pool_results() + _pool_results())

    today = date(2026, 4, 1)
    r1 = await service.get_current_challenges(mock_db, today=today)
    r2 = await service.get_current_challenges(mock_db, today=today)

    assert r1["challenges"] == r2["challenges"]
    assert r1["week"] == r2["week"]


@pytest.mark.asyncio
async def test_different_weeks_different_challenges(service, mock_db):
    """Different weeks should (very likely) select different parameters."""
    mock_db.execute = AsyncMock(side_effect=_pool_results() + _pool_results())

    r1 = await service.get_current_challenges(mock_db, today=date(2026, 1, 5))
    r2 = await service.get_current_challenges(mock_db, today=date(2026, 6, 15))

    # At least one challenge should differ (extremely likely with different seeds)
    ids1 = {c["id"] for c in r1["challenges"]}
    ids2 = {c["id"] for c in r2["challenges"]}
    assert ids1 != ids2


@pytest.mark.asyncio
async def test_challenge_structure(service, mock_db):
    """All 3 challenges have correct template and required fields."""
    mock_db.execute = AsyncMock(side_effect=_pool_results())

    result = await service.get_current_challenges(mock_db, today=date(2026, 4, 1))
    assert len(result["challenges"]) == 3
    assert result["week"] == "2026-W14"

    templates = {c["template"] for c in result["challenges"]}
    assert templates == {"genre", "decade", "director"}

    for c in result["challenges"]:
        assert c["target"] == 5
        assert c["icon"] in ("movie_filter", "history", "person")
        assert len(c["id"]) > 0
        assert len(c["title"]) > 0
        assert len(c["description"]) > 0
        assert len(c["parameter"]) > 0


@pytest.mark.asyncio
async def test_genre_challenge_uses_valid_genre(service, mock_db):
    """Genre challenge parameter comes from the pool."""
    genres = ["Animation", "Documentary", "Horror", "Musical", "Western"]
    mock_db.execute = AsyncMock(side_effect=_pool_results(genres=genres))

    result = await service.get_current_challenges(mock_db, today=date(2026, 4, 1))
    genre_challenge = next(c for c in result["challenges"] if c["template"] == "genre")
    assert genre_challenge["parameter"] in genres


@pytest.mark.asyncio
async def test_progress_no_ratings(service, mock_db):
    """User with no qualifying ratings has zero progress."""
    pool = _pool_results()
    progress = [_progress_result([]) for _ in range(3)]
    mock_db.execute = AsyncMock(side_effect=pool + progress)

    result = await service.get_user_progress(1, mock_db, today=date(2026, 4, 1))
    assert result["user_id"] == 1
    assert result["completed_count"] == 0
    assert result["total_count"] == 3

    for c in result["challenges"]:
        assert c["progress"] == 0
        assert c["completed"] is False
        assert c["qualifying_movie_ids"] == []


@pytest.mark.asyncio
async def test_progress_partial(service, mock_db):
    """User with some qualifying ratings has partial progress."""
    pool = _pool_results()
    progress = [
        _progress_result([10, 20, 30]),  # genre: 3/5
        _progress_result([]),  # decade: 0/5
        _progress_result([40]),  # director: 1/5
    ]
    mock_db.execute = AsyncMock(side_effect=pool + progress)

    result = await service.get_user_progress(1, mock_db, today=date(2026, 4, 1))
    assert result["completed_count"] == 0

    genre_c = next(c for c in result["challenges"] if c["template"] == "genre")
    assert genre_c["progress"] == 3
    assert genre_c["completed"] is False
    assert genre_c["qualifying_movie_ids"] == [10, 20, 30]


@pytest.mark.asyncio
async def test_progress_completed(service, mock_db):
    """User with 5+ qualifying ratings completes a challenge."""
    pool = _pool_results()
    progress = [
        _progress_result([1, 2, 3, 4, 5, 6]),  # genre: 6/5 → completed
        _progress_result([10, 20, 30, 40, 50]),  # decade: 5/5 → completed
        _progress_result([]),  # director: 0/5
    ]
    mock_db.execute = AsyncMock(side_effect=pool + progress)

    result = await service.get_user_progress(1, mock_db, today=date(2026, 4, 1))
    assert result["completed_count"] == 2

    genre_c = next(c for c in result["challenges"] if c["template"] == "genre")
    assert genre_c["progress"] == 6
    assert genre_c["completed"] is True


def test_week_boundaries():
    """Monday-to-Monday boundaries are correct."""
    from datetime import UTC, datetime

    start, end = _week_boundaries(2026, 14)
    assert start == datetime(2026, 3, 30, tzinfo=UTC)
    assert end == datetime(2026, 4, 6, tzinfo=UTC)
    assert (end - start).days == 7


def test_week_key():
    """Week key returns correct ISO week info."""
    year, week, label = _week_key(date(2026, 4, 1))
    assert year == 2026
    assert week == 14
    assert label == "2026-W14"
