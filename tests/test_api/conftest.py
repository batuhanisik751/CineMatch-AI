"""Shared fixtures for API tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cinematch.api.deps import (
    get_content_recommender,
    get_db,
    get_hybrid_recommender,
    get_llm_service,
    get_movie_service,
    get_rating_service,
)
from cinematch.main import create_app


def _make_movie(id: int = 1, title: str = "The Matrix") -> MagicMock:
    m = MagicMock()
    m.id = id
    m.tmdb_id = 603
    m.imdb_id = "tt0133093"
    m.movielens_id = 2571
    m.title = title
    m.overview = "A computer hacker discovers reality is a simulation."
    m.genres = ["Action", "Sci-Fi"]
    m.keywords = ["hacker", "simulation"]
    m.cast_names = ["Keanu Reeves"]
    m.director = "Lana Wachowski"
    m.release_date = date(1999, 3, 31)
    m.vote_average = 8.2
    m.vote_count = 20000
    m.popularity = 50.0
    m.poster_path = "/poster.jpg"
    m.embedding = None
    m.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    return m


def _make_rating(user_id: int = 1, movie_id: int = 1, rating: float = 4.5) -> MagicMock:
    r = MagicMock()
    r.id = 1
    r.user_id = user_id
    r.movie_id = movie_id
    r.rating = rating
    r.timestamp = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    r.movie_title = None
    return r


def _make_user(id: int = 1) -> MagicMock:
    u = MagicMock()
    u.id = id
    u.movielens_id = id
    u.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    return u


@pytest.fixture()
def sample_movie():
    return _make_movie()


@pytest.fixture()
def sample_rating():
    return _make_rating()


@pytest.fixture()
def sample_user():
    return _make_user()


@pytest.fixture()
def mock_movie_service(sample_movie):
    svc = AsyncMock()
    svc.get_by_id.return_value = sample_movie
    svc.search_by_title.return_value = ([sample_movie], 1)
    svc.get_movies_by_ids.return_value = {sample_movie.id: sample_movie}
    return svc


@pytest.fixture()
def mock_rating_service(sample_rating):
    svc = AsyncMock()
    svc.add_rating.return_value = sample_rating
    svc.get_user_ratings.return_value = ([(sample_rating, "The Matrix")], 1)
    return svc


@pytest.fixture()
def mock_content_recommender():
    rec = AsyncMock()
    rec.get_similar_movies.return_value = [(2, 0.92), (3, 0.85)]
    return rec


@pytest.fixture()
def mock_hybrid_recommender():
    rec = AsyncMock()
    rec.recommend.return_value = [(1, 0.95), (2, 0.88)]
    return rec


@pytest.fixture()
def mock_llm_service():
    svc = AsyncMock()
    svc.explain_recommendation.return_value = (
        "This movie matches your preferences due to shared sci-fi themes."
    )
    return svc


@pytest.fixture()
def mock_db():
    return AsyncMock()


@pytest.fixture()
def app(
    mock_movie_service,
    mock_rating_service,
    mock_content_recommender,
    mock_hybrid_recommender,
    mock_llm_service,
    mock_db,
):
    test_app = create_app()

    test_app.dependency_overrides[get_db] = lambda: mock_db
    test_app.dependency_overrides[get_movie_service] = lambda: mock_movie_service
    test_app.dependency_overrides[get_rating_service] = lambda: mock_rating_service
    test_app.dependency_overrides[get_content_recommender] = lambda: mock_content_recommender
    test_app.dependency_overrides[get_hybrid_recommender] = lambda: mock_hybrid_recommender
    test_app.dependency_overrides[get_llm_service] = lambda: mock_llm_service

    return test_app


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
