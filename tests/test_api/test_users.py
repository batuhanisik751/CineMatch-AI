"""Tests for user API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock


async def test_get_user_success(client, mock_db, sample_user):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_user
    mock_db.execute = AsyncMock(return_value=result_mock)

    resp = await client.get(f"/api/v1/users/{sample_user.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == sample_user.id
    assert data["movielens_id"] == sample_user.movielens_id


async def test_get_user_not_found(client, mock_db):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result_mock)

    resp = await client.get("/api/v1/users/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"
