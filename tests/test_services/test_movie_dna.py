"""Tests for MovieService.get_movie_dna."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.movie_service import MovieService


def _mock_movie(
    id: int = 1,
    title: str = "The Matrix",
    genres: list[str] | None = None,
    keywords: list[str] | None = None,
    director: str | None = "Lana Wachowski",
    release_date: date | None = date(1999, 3, 31),
    vote_average: float = 8.2,
) -> MagicMock:
    m = MagicMock()
    m.id = id
    m.title = title
    m.genres = ["Action", "Sci-Fi"] if genres is None else genres
    m.keywords = ["hacker", "simulation"] if keywords is None else keywords
    m.director = director
    m.release_date = release_date
    m.vote_average = vote_average
    return m


@pytest.mark.asyncio()
async def test_get_movie_dna_basic():
    svc = MovieService()
    db = AsyncMock()
    content_rec = AsyncMock()

    movie = _mock_movie()
    neighbor1 = _mock_movie(
        id=2,
        title="Blade Runner",
        genres=["Sci-Fi", "Drama"],
        keywords=["dystopia", "android"],
    )
    neighbor2 = _mock_movie(
        id=3,
        title="Inception",
        genres=["Action", "Sci-Fi"],
        keywords=["dream", "simulation"],
    )

    # Mock get_by_id
    db.execute = AsyncMock()
    svc.get_by_id = AsyncMock(return_value=movie)
    svc.get_movies_by_ids = AsyncMock(return_value={2: neighbor1, 3: neighbor2})
    content_rec.get_similar_movies.return_value = [(2, 0.92), (3, 0.85)]

    result = await svc.get_movie_dna(1, db, content_rec)

    assert result is not None
    assert result["movie_id"] == 1
    assert result["title"] == "The Matrix"
    assert result["decade"] == 1990
    assert result["director"] == "Lana Wachowski"
    assert result["vote_average"] == 8.2

    # Genres should include Action, Sci-Fi, Drama
    genre_names = [g["genre"] for g in result["genres"]]
    assert "Sci-Fi" in genre_names
    assert "Action" in genre_names

    # Keywords should be ranked by frequency
    kw_names = [k["keyword"] for k in result["top_keywords"]]
    assert "simulation" in kw_names  # appears in movie + neighbor2

    # Mood tags: keywords in neighbors but not in movie, appearing >=2 times
    # "dystopia" only in 1 neighbor, "android" only in 1, "dream" only in 1
    # So no mood tags meet the >=2 threshold here
    assert isinstance(result["mood_tags"], list)


@pytest.mark.asyncio()
async def test_get_movie_dna_movie_not_found():
    svc = MovieService()
    db = AsyncMock()
    content_rec = AsyncMock()
    svc.get_by_id = AsyncMock(return_value=None)

    result = await svc.get_movie_dna(999, db, content_rec)
    assert result is None


@pytest.mark.asyncio()
async def test_get_movie_dna_no_release_date():
    svc = MovieService()
    db = AsyncMock()
    content_rec = AsyncMock()

    movie = _mock_movie(release_date=None)
    svc.get_by_id = AsyncMock(return_value=movie)
    svc.get_movies_by_ids = AsyncMock(return_value={})
    content_rec.get_similar_movies.return_value = []

    result = await svc.get_movie_dna(1, db, content_rec)
    assert result["decade"] is None


@pytest.mark.asyncio()
async def test_get_movie_dna_empty_genres_keywords():
    svc = MovieService()
    db = AsyncMock()
    content_rec = AsyncMock()

    movie = _mock_movie(genres=[], keywords=[])
    svc.get_by_id = AsyncMock(return_value=movie)
    svc.get_movies_by_ids = AsyncMock(return_value={})
    content_rec.get_similar_movies.return_value = []

    result = await svc.get_movie_dna(1, db, content_rec)
    assert result["genres"] == []
    assert result["top_keywords"] == []
    assert result["mood_tags"] == []


@pytest.mark.asyncio()
async def test_get_movie_dna_mood_tags():
    """Mood tags appear when >=2 neighbors share a keyword not in the movie."""
    svc = MovieService()
    db = AsyncMock()
    content_rec = AsyncMock()

    movie = _mock_movie(keywords=["hacker"])
    n1 = _mock_movie(id=2, keywords=["dystopia", "cyberpunk"])
    n2 = _mock_movie(id=3, keywords=["dystopia", "cyberpunk"])
    n3 = _mock_movie(id=4, keywords=["dystopia"])

    svc.get_by_id = AsyncMock(return_value=movie)
    svc.get_movies_by_ids = AsyncMock(return_value={2: n1, 3: n2, 4: n3})
    content_rec.get_similar_movies.return_value = [(2, 0.9), (3, 0.8), (4, 0.7)]

    result = await svc.get_movie_dna(1, db, content_rec)
    # "dystopia" in 3 neighbors, "cyberpunk" in 2 — both qualify
    assert "dystopia" in result["mood_tags"]
    assert "cyberpunk" in result["mood_tags"]
