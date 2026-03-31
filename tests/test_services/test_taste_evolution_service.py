"""Tests for TasteEvolutionService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.taste_evolution_service import TasteEvolutionService


@pytest.fixture()
def service():
    return TasteEvolutionService()


@pytest.fixture()
def mock_db():
    return AsyncMock()


def _make_row(period: str, genre: str, pct: float):
    row = MagicMock()
    row.period = period
    row.genre = genre
    row.pct = pct
    return row


async def test_no_ratings_returns_empty_periods(service, mock_db):
    result_mock = MagicMock()
    result_mock.all.return_value = []
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_taste_evolution(1, mock_db, granularity="quarter")

    assert result["user_id"] == 1
    assert result["granularity"] == "quarter"
    assert result["periods"] == []


async def test_single_period_genre_distribution(service, mock_db):
    rows = [
        _make_row("2024-Q1", "Action", 60.0),
        _make_row("2024-Q1", "Drama", 40.0),
    ]
    result_mock = MagicMock()
    result_mock.all.return_value = rows
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_taste_evolution(1, mock_db, granularity="quarter")

    assert len(result["periods"]) == 1
    period = result["periods"][0]
    assert period["period"] == "2024-Q1"
    assert period["genres"]["Action"] == 60.0
    assert period["genres"]["Drama"] == 40.0


async def test_multiple_periods_sorted(service, mock_db):
    rows = [
        _make_row("2024-Q2", "Comedy", 50.0),
        _make_row("2024-Q2", "Horror", 50.0),
        _make_row("2024-Q1", "Action", 100.0),
    ]
    result_mock = MagicMock()
    result_mock.all.return_value = rows
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_taste_evolution(1, mock_db, granularity="quarter")

    assert len(result["periods"]) == 2
    assert result["periods"][0]["period"] == "2024-Q1"
    assert result["periods"][1]["period"] == "2024-Q2"


async def test_month_granularity_passthrough(service, mock_db):
    rows = [
        _make_row("2024-01", "Sci-Fi", 100.0),
    ]
    result_mock = MagicMock()
    result_mock.all.return_value = rows
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_taste_evolution(1, mock_db, granularity="month")

    assert result["granularity"] == "month"
    assert result["periods"][0]["period"] == "2024-01"


async def test_year_granularity_passthrough(service, mock_db):
    rows = [
        _make_row("2024", "Drama", 70.0),
        _make_row("2024", "Action", 30.0),
    ]
    result_mock = MagicMock()
    result_mock.all.return_value = rows
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_taste_evolution(1, mock_db, granularity="year")

    assert result["granularity"] == "year"
    assert result["periods"][0]["genres"]["Drama"] == 70.0
