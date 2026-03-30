"""Shared fixtures for API tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from cinematch.api.deps import (
    get_cache_service,
    get_content_recommender,
    get_db,
    get_embedding_service,
    get_hybrid_recommender,
    get_llm_service,
    get_movie_service,
    get_rating_service,
    get_user_stats_service,
    get_watchlist_service,
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


def _make_rating(user_id: int = 1, movie_id: int = 1, rating: int = 9) -> MagicMock:
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
    svc.list_movies.return_value = ([sample_movie], 1)
    svc.get_genre_counts.return_value = [("Action", 50), ("Sci-Fi", 30)]
    svc.semantic_search.return_value = []
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
    from cinematch.services.hybrid_recommender import (
        RecommendationResult,
        ScoreBreakdown,
        SeedInfluence,
    )

    rec = AsyncMock()
    rec.recommend.return_value = [
        RecommendationResult(
            movie_id=1,
            score=0.95,
            because_you_liked=SeedInfluence(movie_id=10, title="Inception", your_rating=9.0),
            feature_explanations=["Matches your love of Action and Sci-Fi"],
            score_breakdown=ScoreBreakdown(content_score=0.8, collab_score=0.7, alpha=0.5),
        ),
        RecommendationResult(
            movie_id=2,
            score=0.88,
            score_breakdown=ScoreBreakdown(content_score=0.6, collab_score=0.9, alpha=0.5),
        ),
    ]
    rec.mood_recommend.return_value = ([(1, 0.92), (2, 0.85)], True)
    return rec


@pytest.fixture()
def mock_cache_service():
    svc = AsyncMock()
    svc.get.return_value = None
    svc.set.return_value = None
    return svc


@pytest.fixture()
def mock_llm_service():
    svc = AsyncMock()
    svc.explain_recommendation.return_value = (
        "This movie matches your preferences due to shared sci-fi themes."
    )
    return svc


@pytest.fixture()
def mock_embedding_service():
    svc = MagicMock()
    svc.embed_text.return_value = np.zeros(384, dtype=np.float32)
    return svc


def _make_watchlist_item(user_id: int = 1, movie_id: int = 1) -> MagicMock:
    w = MagicMock()
    w.id = 1
    w.user_id = user_id
    w.movie_id = movie_id
    w.added_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    # These fields aren't on the ORM model — set to None so Pydantic doesn't
    # pick up MagicMock auto-attributes during model_validate(from_attributes).
    w.movie_title = None
    w.poster_path = None
    w.genres = []
    w.vote_average = 0.0
    w.release_date = None
    return w


@pytest.fixture()
def sample_watchlist_item():
    return _make_watchlist_item()


@pytest.fixture()
def mock_watchlist_service(sample_watchlist_item, sample_movie):
    svc = AsyncMock()
    svc.add_to_watchlist.return_value = sample_watchlist_item
    svc.remove_from_watchlist.return_value = True
    svc.get_watchlist.return_value = (
        [
            (
                sample_watchlist_item,
                "The Matrix",
                "/poster.jpg",
                ["Action", "Sci-Fi"],
                8.2,
                date(1999, 3, 31),
            )
        ],
        1,
    )
    svc.is_in_watchlist.return_value = True
    svc.bulk_check.return_value = {1}
    return svc


@pytest.fixture()
def mock_user_stats_service():
    svc = AsyncMock()
    svc.get_user_stats.return_value = {
        "user_id": 1,
        "total_ratings": 5,
        "average_rating": 3.8,
        "genre_distribution": [
            {"genre": "Action", "count": 3, "percentage": 60.0},
            {"genre": "Comedy", "count": 2, "percentage": 40.0},
        ],
        "rating_distribution": [{"rating": str(v), "count": 0} for v in range(1, 11)],
        "top_directors": [{"name": "Nolan", "count": 3}],
        "top_actors": [{"name": "DiCaprio", "count": 2}],
        "rating_timeline": [{"month": "2024-01", "count": 5}],
    }
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
    mock_embedding_service,
    mock_user_stats_service,
    mock_watchlist_service,
    mock_cache_service,
    mock_db,
):
    test_app = create_app()

    test_app.dependency_overrides[get_db] = lambda: mock_db
    test_app.dependency_overrides[get_movie_service] = lambda: mock_movie_service
    test_app.dependency_overrides[get_rating_service] = lambda: mock_rating_service
    test_app.dependency_overrides[get_content_recommender] = lambda: mock_content_recommender
    test_app.dependency_overrides[get_hybrid_recommender] = lambda: mock_hybrid_recommender
    test_app.dependency_overrides[get_llm_service] = lambda: mock_llm_service
    test_app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service
    test_app.dependency_overrides[get_user_stats_service] = lambda: mock_user_stats_service
    test_app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service
    test_app.dependency_overrides[get_cache_service] = lambda: mock_cache_service

    return test_app


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
