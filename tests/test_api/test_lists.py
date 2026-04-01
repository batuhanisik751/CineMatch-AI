"""Tests for custom user lists API endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_list_success(client, sample_user_list):
    resp = await client.post(
        "/api/v1/users/1/lists",
        json={"name": "Favorites", "description": "My faves", "is_public": False},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Favorites"
    assert data["user_id"] == 1
    assert data["movie_count"] == 0
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_user_lists_success(client):
    resp = await client.get("/api/v1/users/1/lists")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["total"] == 1
    assert len(data["lists"]) == 1
    assert data["lists"][0]["name"] == "Favorites"


@pytest.mark.asyncio
async def test_get_list_detail_success(client):
    resp = await client.get("/api/v1/lists/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "Favorites"
    assert len(data["items"]) == 1
    assert data["items"][0]["movie_title"] == "The Matrix"


@pytest.mark.asyncio
async def test_get_list_not_found(client, mock_user_list_service):
    mock_user_list_service.get_list.return_value = None
    resp = await client.get("/api/v1/lists/999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_list_success(client):
    resp = await client.patch(
        "/api/v1/users/1/lists/1",
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Favorites"  # mock returns original


@pytest.mark.asyncio
async def test_update_list_not_found(client, mock_user_list_service):
    mock_user_list_service.update_list.return_value = None
    resp = await client.patch(
        "/api/v1/users/1/lists/999",
        json={"name": "No List"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_list_success(client):
    resp = await client.delete("/api/v1/users/1/lists/1")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_list_not_found(client, mock_user_list_service):
    mock_user_list_service.delete_list.return_value = False
    resp = await client.delete("/api/v1/users/1/lists/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_item_success(client, sample_list_item, sample_movie):
    resp = await client.post(
        "/api/v1/users/1/lists/1/items",
        json={"movie_id": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["movie_id"] == 1
    assert data["movie_title"] == sample_movie.title


@pytest.mark.asyncio
async def test_add_item_movie_not_found(client, mock_movie_service):
    mock_movie_service.get_by_id.return_value = None
    resp = await client.post(
        "/api/v1/users/1/lists/1/items",
        json={"movie_id": 999},
    )
    assert resp.status_code == 404
    assert "Movie not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_item_list_not_found(client, mock_user_list_service):
    mock_user_list_service.add_item.return_value = None
    resp = await client.post(
        "/api/v1/users/1/lists/999/items",
        json={"movie_id": 1},
    )
    assert resp.status_code == 404
    assert "not owned" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_remove_item_success(client):
    resp = await client.delete("/api/v1/users/1/lists/1/items/1")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_remove_item_not_found(client, mock_user_list_service):
    mock_user_list_service.remove_item.return_value = False
    resp = await client.delete("/api/v1/users/1/lists/1/items/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reorder_items_success(client):
    resp = await client.put(
        "/api/v1/users/1/lists/1/items/reorder",
        json={"movie_ids": [2, 1]},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_reorder_items_not_found(client, mock_user_list_service):
    mock_user_list_service.reorder_items.return_value = False
    resp = await client.put(
        "/api/v1/users/1/lists/999/items/reorder",
        json={"movie_ids": [1]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_popular_lists(client):
    resp = await client.get("/api/v1/lists/popular")
    assert resp.status_code == 200
    data = resp.json()
    assert "lists" in data
    assert data["total"] == 1
    assert len(data["lists"]) == 1
