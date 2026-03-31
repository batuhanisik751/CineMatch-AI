"""Tests for UserStatsService.get_affinities."""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.user_stats_service import UserStatsService


@pytest.fixture()
def service():
    return UserStatsService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


async def test_affinities_empty_for_no_ratings(service, mock_db):
    """User with 0 ratings returns empty affinities."""
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    mock_db.execute = AsyncMock(return_value=count_result)

    result = await service.get_affinities(1, mock_db)

    assert result["user_id"] == 1
    assert result["directors"] == []
    assert result["actors"] == []


async def test_affinities_returns_directors_and_actors(service, mock_db):
    """Full affinity data with directors and actors."""
    # Mock: total count > 0
    count_result = MagicMock()
    count_result.scalar.return_value = 10

    # Mock: director aggregates
    dir_agg_result = MagicMock()
    dir_agg_result.all.return_value = [("Nolan", 8.5, 3)]

    # Mock: director films
    dir_films_result = MagicMock()
    dir_films_result.all.return_value = [
        (1, "Inception", 9, "/inception.jpg"),
        (2, "Interstellar", 8, "/interstellar.jpg"),
        (3, "Tenet", 8, None),
    ]

    # Mock: actor aggregates
    act_agg_result = MagicMock()
    act_agg_result.all.return_value = [("DiCaprio", 7.5, 2)]

    # Mock: actor films
    act_films_result = MagicMock()
    act_films_result.all.return_value = [
        (1, "Inception", 9, "/inception.jpg"),
        (4, "Shutter Island", 6, "/shutter.jpg"),
    ]

    mock_db.execute = AsyncMock(
        side_effect=[
            count_result,
            dir_agg_result,
            dir_films_result,
            act_agg_result,
            act_films_result,
        ]
    )

    result = await service.get_affinities(1, mock_db, limit=10)

    assert result["user_id"] == 1
    assert len(result["directors"]) == 1
    d = result["directors"][0]
    assert d["name"] == "Nolan"
    assert d["role"] == "director"
    assert d["avg_rating"] == 8.5
    assert d["count"] == 3
    assert d["weighted_score"] == round(8.5 * math.log(4), 2)
    assert len(d["films_rated"]) == 3
    assert d["films_rated"][0]["title"] == "Inception"

    assert len(result["actors"]) == 1
    a = result["actors"][0]
    assert a["name"] == "DiCaprio"
    assert a["role"] == "actor"
    assert a["avg_rating"] == 7.5
    assert a["count"] == 2
    assert a["weighted_score"] == round(7.5 * math.log(3), 2)
    assert len(a["films_rated"]) == 2


async def test_affinities_no_directors(service, mock_db):
    """User has actor affinities but no directors meeting the threshold."""
    count_result = MagicMock()
    count_result.scalar.return_value = 5

    dir_agg_result = MagicMock()
    dir_agg_result.all.return_value = []

    act_agg_result = MagicMock()
    act_agg_result.all.return_value = [("Actor A", 9.0, 2)]

    act_films_result = MagicMock()
    act_films_result.all.return_value = [
        (10, "Film X", 9, None),
        (11, "Film Y", 9, None),
    ]

    mock_db.execute = AsyncMock(
        side_effect=[count_result, dir_agg_result, act_agg_result, act_films_result]
    )

    result = await service.get_affinities(1, mock_db)

    assert result["directors"] == []
    assert len(result["actors"]) == 1
    assert result["actors"][0]["name"] == "Actor A"
