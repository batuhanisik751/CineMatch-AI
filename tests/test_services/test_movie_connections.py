"""Tests for MovieService movie connection methods."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.movie_service import MovieService


def _mock_movie(
    id: int = 1,
    title: str = "Movie A",
    cast_names: list[str] | None = None,
    director: str | None = None,
    genres: list[str] | None = None,
    keywords: list[str] | None = None,
) -> MagicMock:
    m = MagicMock()
    m.id = id
    m.title = title
    m.cast_names = cast_names or []
    m.director = director
    m.genres = genres or []
    m.keywords = keywords or []
    m.vote_average = 7.0
    m.release_date = None
    m.poster_path = None
    return m


@pytest.fixture()
def service():
    return MovieService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


# --- Direct connections ---


async def test_find_direct_connections_shared_actors(service, mock_db):
    m1 = _mock_movie(1, "A", cast_names=["Alice", "Bob", "Charlie"])
    m2 = _mock_movie(2, "B", cast_names=["Bob", "Charlie", "Dave"])

    service.get_by_id = AsyncMock(side_effect=[m1, m2])
    movie1, movie2, connections = await service.find_direct_connections(1, 2, mock_db)

    actor_connections = [c for c in connections if c["type"] == "actor"]
    assert len(actor_connections) == 2
    values = {c["value"] for c in actor_connections}
    assert values == {"Bob", "Charlie"}


async def test_find_direct_connections_same_director(service, mock_db):
    m1 = _mock_movie(1, "A", director="Nolan")
    m2 = _mock_movie(2, "B", director="Nolan")

    service.get_by_id = AsyncMock(side_effect=[m1, m2])
    _, _, connections = await service.find_direct_connections(1, 2, mock_db)

    director_connections = [c for c in connections if c["type"] == "director"]
    assert len(director_connections) == 1
    assert director_connections[0]["value"] == "Nolan"


async def test_find_direct_connections_shared_genres_keywords(service, mock_db):
    m1 = _mock_movie(1, "A", genres=["Action", "Sci-Fi"], keywords=["robot", "future"])
    m2 = _mock_movie(2, "B", genres=["Sci-Fi", "Drama"], keywords=["future", "space"])

    service.get_by_id = AsyncMock(side_effect=[m1, m2])
    _, _, connections = await service.find_direct_connections(1, 2, mock_db)

    genre_conns = [c for c in connections if c["type"] == "genre"]
    keyword_conns = [c for c in connections if c["type"] == "keyword"]
    assert len(genre_conns) == 1
    assert genre_conns[0]["value"] == "Sci-Fi"
    assert len(keyword_conns) == 1
    assert keyword_conns[0]["value"] == "future"


async def test_find_direct_connections_no_overlap(service, mock_db):
    m1 = _mock_movie(1, "A", cast_names=["Alice"], genres=["Action"], keywords=["war"])
    m2 = _mock_movie(2, "B", cast_names=["Bob"], genres=["Comedy"], keywords=["love"])

    service.get_by_id = AsyncMock(side_effect=[m1, m2])
    _, _, connections = await service.find_direct_connections(1, 2, mock_db)

    assert len(connections) == 0


async def test_find_direct_connections_movie_not_found(service, mock_db):
    service.get_by_id = AsyncMock(return_value=None)
    movie1, movie2, connections = await service.find_direct_connections(1, 999, mock_db)

    assert movie1 is None
    assert connections == []


# --- Shortest path ---


async def test_find_shortest_path_direct_link(service, mock_db):
    m1 = _mock_movie(1, "A", cast_names=["Alice"])
    m2 = _mock_movie(2, "B", cast_names=["Alice"])

    service.get_by_id = AsyncMock(side_effect=[m1, m2])
    movie1, movie2, path, found = await service.find_shortest_path(1, 2, mock_db)

    assert found is True
    assert len(path) == 2
    assert path[0]["movie"].id == 1
    assert path[1]["movie"].id == 2
    assert "Alice" in path[1]["linked_by"]


async def test_find_shortest_path_two_hops(service, mock_db):
    m1 = _mock_movie(1, "A", cast_names=["Alice"])
    m2 = _mock_movie(2, "B", cast_names=["Bob"])
    m_bridge = _mock_movie(3, "Bridge", cast_names=["Alice", "Bob"])

    service.get_by_id = AsyncMock(side_effect=[m1, m2])

    # _movies_by_person: Alice -> [m1, m_bridge], Bob -> [m2, m_bridge]
    async def mock_movies_by_person(person_name, db, limit=50):
        if person_name == "Alice":
            return [m1, m_bridge]
        if person_name == "Bob":
            return [m2, m_bridge]
        return []

    service._movies_by_person = AsyncMock(side_effect=mock_movies_by_person)

    _, _, path, found = await service.find_shortest_path(1, 2, mock_db)

    assert found is True
    assert len(path) == 3
    assert path[0]["movie"].id == 1
    assert path[1]["movie"].id == 3
    assert path[2]["movie"].id == 2


async def test_find_shortest_path_not_found(service, mock_db):
    m1 = _mock_movie(1, "A", cast_names=["Alice"])
    m2 = _mock_movie(2, "B", cast_names=["Bob"])

    service.get_by_id = AsyncMock(side_effect=[m1, m2])
    service._movies_by_person = AsyncMock(return_value=[])

    _, _, path, found = await service.find_shortest_path(1, 2, mock_db, max_depth=2)

    assert found is False
    assert path == []
