"""Tests for movie connections and path endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_connection_endpoint_success(client):
    resp = await client.get("/api/v1/movies/1/connection/2")
    assert resp.status_code == 200
    data = resp.json()
    assert "connections" in data
    assert data["connection_count"] == 2
    assert data["connections"][0]["type"] == "actor"
    assert data["connections"][0]["value"] == "Keanu Reeves"


@pytest.mark.asyncio
async def test_connection_endpoint_404(client, mock_movie_service):
    mock_movie_service.find_direct_connections.return_value = (None, None, [])
    resp = await client.get("/api/v1/movies/1/connection/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_path_endpoint_success(client):
    resp = await client.get("/api/v1/movies/1/path/2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert data["degrees"] == 1
    assert len(data["path"]) == 2
    assert data["path"][0]["linked_by"] is None
    assert "Keanu Reeves" in data["path"][1]["linked_by"]


@pytest.mark.asyncio
async def test_path_endpoint_not_found(client, mock_movie_service):
    mock_movie_service.find_shortest_path.return_value = (
        mock_movie_service.get_by_id.return_value,
        mock_movie_service.get_by_id.return_value,
        [],
        False,
    )
    resp = await client.get("/api/v1/movies/1/path/2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert data["degrees"] == 0
    assert data["path"] == []


@pytest.mark.asyncio
async def test_path_endpoint_max_depth_validation(client):
    resp = await client.get("/api/v1/movies/1/path/2?max_depth=10")
    assert resp.status_code == 422
