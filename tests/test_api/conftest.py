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
    get_dismissal_service,
    get_embedding_service,
    get_feed_service,
    get_hybrid_recommender,
    get_llm_service,
    get_movie_service,
    get_rating_service,
    get_streak_service,
    get_taste_profile_service,
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
    svc.trending.return_value = [(sample_movie, 42)]
    svc.hidden_gems.return_value = [sample_movie]
    svc.top_by_genre.return_value = [(sample_movie, 8.5, 150)]
    svc.get_decade_stats.return_value = [(2000, 150, 6.8), (1990, 200, 7.1)]
    svc.top_by_decade.return_value = ([(sample_movie, 8.5, 150)], 1)
    svc.search_directors.return_value = [("Christopher Nolan", 12, 7.84)]
    svc.popular_directors.return_value = [
        ("Christopher Nolan", 12, 7.84),
        ("Steven Spielberg", 30, 7.21),
    ]
    svc.filmography_by_director.return_value = (
        [(sample_movie, None)],
        {
            "total_films": 1,
            "avg_vote": 8.2,
            "genres": ["Action", "Sci-Fi"],
            "user_avg_rating": None,
            "user_rated_count": 0,
        },
    )
    svc.popular_keywords.return_value = [("time travel", 42), ("dystopia", 35)]
    svc.search_keywords.return_value = [("time travel", 42)]
    svc.movies_by_keyword.return_value = (
        [sample_movie],
        1,
        {"total_movies": 1, "avg_vote": 8.2, "top_genres": ["Action", "Sci-Fi"]},
    )
    svc.surprise_movies.return_value = [sample_movie]
    svc.advanced_search.return_value = ([sample_movie], 1)
    svc.controversial.return_value = [(sample_movie, 7.3, 2.15, 150, {r: 15 for r in range(1, 11)})]
    svc.collection_completions.return_value = [
        {
            "creator_type": "director",
            "creator_name": "Lana Wachowski",
            "rated_count": 3,
            "avg_rating": 8.0,
            "total_by_creator": 5,
            "missing": [sample_movie],
        }
    ]
    svc.search_actors.return_value = [("Keanu Reeves", 8, 7.15)]
    svc.popular_actors.return_value = [
        ("Keanu Reeves", 8, 7.15),
        ("Tom Hanks", 25, 7.42),
    ]
    svc.filmography_by_actor.return_value = (
        [(sample_movie, None)],
        {
            "total_films": 1,
            "avg_vote": 8.2,
            "genres": ["Action", "Sci-Fi"],
            "user_avg_rating": None,
            "user_rated_count": 0,
        },
    )
    return svc


@pytest.fixture()
def mock_rating_service(sample_rating):
    svc = AsyncMock()
    svc.add_rating.return_value = sample_rating
    svc.get_user_ratings.return_value = ([(sample_rating, "The Matrix")], 1)
    svc.bulk_check.return_value = {1: 9}
    svc.get_rated_movie_ids.return_value = {1}
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
    rec.from_seed_recommend.return_value = [
        RecommendationResult(
            movie_id=1,
            score=0.90,
            because_you_liked=SeedInfluence(movie_id=5, title="The Matrix", your_rating=10.0),
            feature_explanations=["Same director as The Matrix — Lana Wachowski"],
            score_breakdown=ScoreBreakdown(content_score=0.85, collab_score=0.6, alpha=0.5),
        ),
    ]
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
    svc.get_affinities.return_value = {
        "user_id": 1,
        "directors": [],
        "actors": [],
    }
    return svc


def _make_dismissal(user_id: int = 1, movie_id: int = 1) -> MagicMock:
    d = MagicMock()
    d.id = 1
    d.user_id = user_id
    d.movie_id = movie_id
    d.dismissed_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    d.movie_title = None
    d.poster_path = None
    d.genres = []
    d.vote_average = 0.0
    d.release_date = None
    return d


@pytest.fixture()
def sample_dismissal():
    return _make_dismissal()


@pytest.fixture()
def mock_dismissal_service(sample_dismissal):
    svc = AsyncMock()
    svc.dismiss_movie.return_value = sample_dismissal
    svc.undismiss_movie.return_value = True
    svc.get_dismissed_movie_ids.return_value = {1}
    svc.get_dismissals.return_value = (
        [
            (
                sample_dismissal,
                "The Matrix",
                "/poster.jpg",
                ["Action", "Sci-Fi"],
                8.2,
                date(1999, 3, 31),
            )
        ],
        1,
    )
    svc.bulk_check.return_value = {1}
    return svc


@pytest.fixture()
def mock_taste_profile_service():
    svc = AsyncMock()
    svc.get_taste_profile.return_value = {
        "user_id": 1,
        "total_ratings": 20,
        "insights": [
            {
                "key": "top_genre",
                "icon": "movie_filter",
                "text": "You're a Thriller enthusiast (35.0% of your ratings)",
            },
            {
                "key": "critic_style",
                "icon": "thumbs_up_down",
                "text": "You're a generous critic (avg 7.2 vs site avg 6.5)",
            },
            {
                "key": "director_affinity",
                "icon": "person",
                "text": "You have a special appreciation for Nolan's work (5 films rated)",
            },
            {
                "key": "decade_preference",
                "icon": "calendar_month",
                "text": "Your sweet spot is 2000s cinema",
            },
        ],
        "llm_summary": None,
    }
    return svc


@pytest.fixture()
def mock_streak_service():
    svc = AsyncMock()
    svc.get_streaks.return_value = {
        "user_id": 1,
        "current_streak": 5,
        "longest_streak": 12,
        "total_ratings": 87,
        "milestones": [
            {"threshold": 10, "reached": True, "label": "10 Ratings"},
            {"threshold": 25, "reached": True, "label": "25 Ratings"},
            {"threshold": 50, "reached": True, "label": "50 Ratings"},
            {"threshold": 100, "reached": False, "label": "100 Ratings"},
            {"threshold": 250, "reached": False, "label": "250 Ratings"},
            {"threshold": 500, "reached": False, "label": "500 Ratings"},
            {"threshold": 1000, "reached": False, "label": "1000 Ratings"},
        ],
    }
    return svc


@pytest.fixture()
def mock_feed_service(sample_movie):
    from cinematch.schemas.movie import MovieSummary
    from cinematch.schemas.user import FeedResponse, FeedSection

    svc = AsyncMock()
    movie_summary = MovieSummary.model_validate(sample_movie)
    svc.generate_feed.return_value = FeedResponse(
        user_id=1,
        is_personalized=True,
        sections=[
            FeedSection(
                key="because_you_rated",
                title="Because you rated The Matrix highly",
                movies=[movie_summary],
            ),
            FeedSection(
                key="trending_for_you",
                title="Trending with users like you",
                movies=[movie_summary],
            ),
            FeedSection(
                key="hidden_gems",
                title="Hidden gems in Action",
                movies=[movie_summary],
            ),
            FeedSection(
                key="something_different",
                title="Something different",
                movies=[movie_summary],
            ),
            FeedSection(
                key="new_in_decade",
                title="New to you in the 1990s",
                movies=[movie_summary],
            ),
        ],
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
    mock_embedding_service,
    mock_user_stats_service,
    mock_watchlist_service,
    mock_dismissal_service,
    mock_cache_service,
    mock_feed_service,
    mock_taste_profile_service,
    mock_streak_service,
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
    test_app.dependency_overrides[get_dismissal_service] = lambda: mock_dismissal_service
    test_app.dependency_overrides[get_cache_service] = lambda: mock_cache_service
    test_app.dependency_overrides[get_feed_service] = lambda: mock_feed_service
    test_app.dependency_overrides[get_taste_profile_service] = lambda: mock_taste_profile_service
    test_app.dependency_overrides[get_streak_service] = lambda: mock_streak_service

    return test_app


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
