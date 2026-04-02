"""Tests for MovieService.movies_by_cast_combination."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.movie_service import MovieService


def _mock_movie(id: int = 1, title: str = "Inception") -> MagicMock:
    m = MagicMock()
    m.id = id
    m.title = title
    m.popularity = 80.0
    m.vote_average = 8.4
    m.release_date = None
    m.cast_names = ["Leonardo DiCaprio", "Tom Hardy"]
    m.director = "Christopher Nolan"
    return m


@pytest.fixture()
def service():
    return MovieService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


async def test_two_actors_returns_results(service, mock_db):
    movie = _mock_movie()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie]

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.movies_by_cast_combination(
        mock_db, actors=["Leonardo DiCaprio", "Tom Hardy"]
    )

    assert total == 1
    assert movies == [movie]
    assert mock_db.execute.call_count == 2


async def test_three_actors_issues_three_filters(service, mock_db):
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.movies_by_cast_combination(mock_db, actors=["A", "B", "C"])

    assert total == 0
    assert movies == []


async def test_empty_results(service, mock_db):
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.movies_by_cast_combination(
        mock_db, actors=["Unknown Actor", "Another Unknown"]
    )

    assert total == 0
    assert movies == []


async def test_pagination_params_passed(service, mock_db):
    count_result = MagicMock()
    count_result.scalar_one.return_value = 50

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.movies_by_cast_combination(
        mock_db,
        actors=["A", "B"],
        sort_by="vote_average",
        sort_order="asc",
        offset=20,
        limit=10,
    )

    assert total == 50
    assert mock_db.execute.call_count == 2


async def test_multiple_results(service, mock_db):
    movie1 = _mock_movie(id=1, title="Inception")
    movie2 = _mock_movie(id=2, title="The Revenant")

    count_result = MagicMock()
    count_result.scalar_one.return_value = 2

    results_result = MagicMock()
    results_result.scalars.return_value.all.return_value = [movie1, movie2]

    mock_db.execute = AsyncMock(side_effect=[count_result, results_result])

    movies, total = await service.movies_by_cast_combination(
        mock_db, actors=["Leonardo DiCaprio", "Tom Hardy"]
    )

    assert total == 2
    assert len(movies) == 2
    assert movies[0].title == "Inception"
    assert movies[1].title == "The Revenant"
