"""Tests for FeedService."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.feed_service import FeedService


def _make_movie(id: int = 1, title: str = "The Matrix", release_date=None):
    m = MagicMock()
    m.id = id
    m.title = title
    m.genres = ["Action", "Sci-Fi"]
    m.vote_average = 8.2
    m.vote_count = 20000
    m.release_date = release_date or date(1999, 3, 31)
    m.poster_path = "/poster.jpg"
    m.original_language = "en"
    return m


def _make_stats(total_ratings=5, genres=None):
    return {
        "user_id": 1,
        "total_ratings": total_ratings,
        "average_rating": 7.5,
        "genre_distribution": genres
        or [
            {"genre": "Action", "count": 3, "percentage": 60.0},
            {"genre": "Comedy", "count": 2, "percentage": 40.0},
        ],
        "rating_distribution": [],
        "top_directors": [],
        "top_actors": [],
        "rating_timeline": [],
    }


def _mock_db_with_rated_ids(rated_ids: list[int]):
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.all.return_value = [(mid,) for mid in rated_ids]
    db.execute = AsyncMock(return_value=result_mock)
    return db


@pytest.fixture()
def movie_service():
    svc = AsyncMock()
    movie = _make_movie()
    movie2 = _make_movie(id=2, title="Inception")
    svc.get_by_id.return_value = movie
    svc.get_movies_by_ids.return_value = {2: movie2, 3: _make_movie(id=3, title="Blade Runner")}
    svc.trending.return_value = [(movie, 42), (movie2, 30)]
    svc.hidden_gems.return_value = [movie2, _make_movie(id=3, title="Blade Runner")]
    svc.surprise_movies.return_value = [_make_movie(id=4, title="Amélie")]
    svc.top_by_decade.return_value = (
        [(movie2, 8.5, 150), (_make_movie(id=3, title="Blade Runner"), 8.1, 100)],
        2,
    )
    svc.list_movies.return_value = ([movie], 1)
    return svc


@pytest.fixture()
def stats_service():
    svc = AsyncMock()
    svc.get_user_stats.return_value = _make_stats()
    return svc


@pytest.fixture()
def content_recommender():
    rec = AsyncMock()
    rec.get_similar_movies.return_value = [(2, 0.92), (3, 0.85)]
    return rec


@pytest.fixture()
def collab_recommender():
    rec = MagicMock()
    rec.is_known_user.return_value = True
    rec.recommend_for_user.return_value = [(1, 0.9), (2, 0.8), (3, 0.7)]
    return rec


@pytest.fixture()
def hybrid_recommender():
    rec = AsyncMock()
    rec._get_user_top_rated_diverse.return_value = [(1, 9.0), (5, 8.0)]
    return rec


@pytest.fixture()
def feed_service(
    movie_service, stats_service, content_recommender, collab_recommender, hybrid_recommender
):
    return FeedService(
        movie_service=movie_service,
        user_stats_service=stats_service,
        content_recommender=content_recommender,
        collab_recommender=collab_recommender,
        hybrid_recommender=hybrid_recommender,
    )


@pytest.mark.asyncio
async def test_personalized_feed_all_sections(feed_service, movie_service):
    db = _mock_db_with_rated_ids([10, 20])
    result = await feed_service.generate_feed(user_id=1, db=db)

    assert result.is_personalized is True
    assert result.user_id == 1
    assert len(result.sections) == 5

    keys = [s.key for s in result.sections]
    assert "because_you_rated" in keys
    assert "trending_for_you" in keys
    assert "hidden_gems" in keys
    assert "something_different" in keys
    assert "new_in_decade" in keys

    # Each section should have movies
    for section in result.sections:
        assert len(section.movies) > 0
        assert section.title  # non-empty title


@pytest.mark.asyncio
async def test_cold_start_fallback(feed_service, stats_service):
    stats_service.get_user_stats.return_value = _make_stats(total_ratings=0)
    db = AsyncMock()

    result = await feed_service.generate_feed(user_id=999, db=db)

    assert result.is_personalized is False
    assert result.user_id == 999
    keys = [s.key for s in result.sections]
    assert "trending" in keys
    assert "top_rated" in keys
    assert "hidden_gems" in keys


@pytest.mark.asyncio
async def test_graceful_degradation_content_recommender_none(
    movie_service, stats_service, collab_recommender, hybrid_recommender
):
    """Without content recommender, 'because you rated' section is skipped."""
    svc = FeedService(
        movie_service=movie_service,
        user_stats_service=stats_service,
        content_recommender=None,
        collab_recommender=collab_recommender,
        hybrid_recommender=hybrid_recommender,
    )
    db = _mock_db_with_rated_ids([10])
    result = await svc.generate_feed(user_id=1, db=db)

    assert result.is_personalized is True
    keys = [s.key for s in result.sections]
    assert "because_you_rated" not in keys


@pytest.mark.asyncio
async def test_graceful_degradation_collab_unknown_user(
    movie_service, stats_service, content_recommender, hybrid_recommender
):
    """When collab doesn't know user, 'trending for you' section is skipped."""
    collab = MagicMock()
    collab.is_known_user.return_value = False

    svc = FeedService(
        movie_service=movie_service,
        user_stats_service=stats_service,
        content_recommender=content_recommender,
        collab_recommender=collab,
        hybrid_recommender=hybrid_recommender,
    )
    db = _mock_db_with_rated_ids([10])
    result = await svc.generate_feed(user_id=1, db=db)

    assert result.is_personalized is True
    keys = [s.key for s in result.sections]
    assert "trending_for_you" not in keys


@pytest.mark.asyncio
async def test_rated_movies_excluded(feed_service, content_recommender):
    """Movies the user already rated should not appear in feed sections."""
    # User has rated movie IDs 2 and 3, which are what content_recommender returns
    db = _mock_db_with_rated_ids([2, 3])

    # Content recommender returns movies 2 and 3 (both rated)
    content_recommender.get_similar_movies.return_value = [(2, 0.92), (3, 0.85)]

    result = await feed_service.generate_feed(user_id=1, db=db)

    # The "because_you_rated" section should be skipped (all candidates rated)
    keys = [s.key for s in result.sections]
    if "because_you_rated" in keys:
        section = next(s for s in result.sections if s.key == "because_you_rated")
        rated_ids = {2, 3}
        for movie in section.movies:
            assert movie.id not in rated_ids


@pytest.mark.asyncio
async def test_sections_parameter(feed_service):
    """Requesting fewer sections limits the output."""
    db = _mock_db_with_rated_ids([10])
    result = await feed_service.generate_feed(user_id=1, db=db, sections=2)

    # Should have at most 2 sections
    assert len(result.sections) <= 2
