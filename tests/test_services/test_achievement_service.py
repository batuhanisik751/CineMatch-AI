"""Tests for AchievementService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.achievement_service import AchievementService


@pytest.fixture()
def service():
    return AchievementService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


def _basic_row(total: int, avg: float):
    row = MagicMock()
    row.__getitem__ = lambda self, i: [total, avg][i]
    return row


def _scalar_result(value: int):
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _ts_row(night: int, weekend: int, streak: int):
    row = MagicMock()
    row.__getitem__ = lambda self, i: [night, weekend, streak][i]
    return row


def _setup_db(
    mock_db,
    *,
    total: int = 0,
    avg: float = 0.0,
    genres: int = 0,
    decades: int = 0,
    director_rows: list | None = None,
    night: int = 0,
    weekend: int = 0,
    streak: int = 0,
):
    """Configure mock_db to return values for all 5 queries in order."""
    basic_result = MagicMock()
    basic_result.one.return_value = _basic_row(total, avg)

    genre_result = _scalar_result(genres)
    decade_result = _scalar_result(decades)

    director_result = MagicMock()
    rows = []
    for name, rated, db_total in director_rows or []:
        r = MagicMock()
        r.__getitem__ = lambda self, i, n=name, rc=rated, tc=db_total: [n, rc, tc][i]
        rows.append(r)
    director_result.all.return_value = rows

    ts_result = MagicMock()
    ts_result.one.return_value = _ts_row(night, weekend, streak)

    mock_db.execute = AsyncMock(
        side_effect=[basic_result, genre_result, decade_result, director_result, ts_result]
    )


@pytest.mark.asyncio
async def test_no_ratings(service, mock_db):
    _setup_db(mock_db)
    result = await service.get_achievements(1, mock_db)

    assert result["user_id"] == 1
    assert result["total_count"] == 12
    assert result["unlocked_count"] == 0
    assert all(not b["unlocked"] for b in result["badges"])


@pytest.mark.asyncio
async def test_first_rating_only(service, mock_db):
    _setup_db(mock_db, total=1, avg=7.0, genres=1, decades=1)
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["first_rating"]["unlocked"] is True
    assert badges["first_rating"]["progress"] == 1
    assert badges["century_club"]["unlocked"] is False
    assert badges["century_club"]["progress"] == 1
    assert result["unlocked_count"] == 1


@pytest.mark.asyncio
async def test_century_club(service, mock_db):
    _setup_db(mock_db, total=100, avg=6.5, genres=5, decades=3)
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["first_rating"]["unlocked"] is True
    assert badges["century_club"]["unlocked"] is True
    assert badges["marathon_runner"]["unlocked"] is False
    assert badges["marathon_runner"]["progress"] == 100


@pytest.mark.asyncio
async def test_marathon_runner(service, mock_db):
    _setup_db(mock_db, total=500, avg=6.0, genres=5, decades=3)
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["marathon_runner"]["unlocked"] is True
    assert badges["marathon_runner"]["progress"] == 500


@pytest.mark.asyncio
async def test_genre_explorer(service, mock_db):
    _setup_db(mock_db, total=50, avg=6.0, genres=12, decades=3)
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["genre_explorer"]["unlocked"] is True
    assert badges["genre_explorer"]["progress"] == 10
    assert "12 genres" in badges["genre_explorer"]["unlocked_detail"]


@pytest.mark.asyncio
async def test_decade_hopper(service, mock_db):
    _setup_db(mock_db, total=50, avg=6.0, genres=3, decades=6)
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["decade_hopper"]["unlocked"] is True
    assert "6 decades" in badges["decade_hopper"]["unlocked_detail"]


@pytest.mark.asyncio
async def test_director_devotee(service, mock_db):
    _setup_db(
        mock_db,
        total=20,
        avg=7.0,
        genres=3,
        decades=2,
        director_rows=[("Christopher Nolan", 7, 12)],
    )
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["director_devotee"]["unlocked"] is True
    assert "Nolan" in badges["director_devotee"]["unlocked_detail"]
    assert badges["director_devotee"]["progress"] == 5


@pytest.mark.asyncio
async def test_the_critic(service, mock_db):
    _setup_db(mock_db, total=60, avg=4.2, genres=5, decades=3)
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["the_critic"]["unlocked"] is True
    assert "4.2" in badges["the_critic"]["unlocked_detail"]


@pytest.mark.asyncio
async def test_easy_to_please(service, mock_db):
    _setup_db(mock_db, total=60, avg=8.5, genres=5, decades=3)
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["easy_to_please"]["unlocked"] is True
    assert "8.5" in badges["easy_to_please"]["unlocked_detail"]


@pytest.mark.asyncio
async def test_weekend_warrior(service, mock_db):
    _setup_db(mock_db, total=10, avg=7.0, genres=3, decades=2, weekend=6)
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["weekend_warrior"]["unlocked"] is True
    assert badges["weekend_warrior"]["progress"] == 5


@pytest.mark.asyncio
async def test_night_owl(service, mock_db):
    _setup_db(mock_db, total=15, avg=7.0, genres=3, decades=2, night=15)
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["night_owl"]["unlocked"] is True
    assert "15 late-night" in badges["night_owl"]["unlocked_detail"]


@pytest.mark.asyncio
async def test_streak_master(service, mock_db):
    _setup_db(mock_db, total=10, avg=7.0, genres=3, decades=2, streak=10)
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["streak_master"]["unlocked"] is True
    assert "10-day" in badges["streak_master"]["unlocked_detail"]


@pytest.mark.asyncio
async def test_completionist(service, mock_db):
    _setup_db(
        mock_db,
        total=10,
        avg=7.0,
        genres=3,
        decades=2,
        director_rows=[("Denis Villeneuve", 6, 6)],
    )
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["completionist"]["unlocked"] is True
    assert badges["completionist"]["unlocked_detail"] == "Denis Villeneuve"


@pytest.mark.asyncio
async def test_all_badges_unlocked(service, mock_db):
    _setup_db(
        mock_db,
        total=500,
        avg=4.5,
        genres=15,
        decades=7,
        director_rows=[("Christopher Nolan", 12, 12)],
        night=20,
        weekend=8,
        streak=14,
    )
    result = await service.get_achievements(1, mock_db)

    # first_rating, century_club, marathon_runner, genre_explorer, decade_hopper,
    # director_devotee, the_critic, weekend_warrior, night_owl, streak_master,
    # completionist = 11 (easy_to_please won't unlock because avg < 5)
    assert result["unlocked_count"] == 11
    badges = {b["id"]: b for b in result["badges"]}
    assert badges["easy_to_please"]["unlocked"] is False


@pytest.mark.asyncio
async def test_progress_values_partial(service, mock_db):
    _setup_db(mock_db, total=42, avg=6.5, genres=7, decades=3)
    result = await service.get_achievements(1, mock_db)

    badges = {b["id"]: b for b in result["badges"]}
    assert badges["first_rating"]["progress"] == 1
    assert badges["century_club"]["progress"] == 42
    assert badges["marathon_runner"]["progress"] == 42
    assert badges["genre_explorer"]["progress"] == 7
    assert badges["decade_hopper"]["progress"] == 3
    assert badges["the_critic"]["progress"] == 42
    assert badges["easy_to_please"]["progress"] == 42
