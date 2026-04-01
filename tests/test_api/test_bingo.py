"""Tests for the bingo API endpoint."""

from __future__ import annotations

import json

import pytest


@pytest.mark.asyncio
async def test_get_bingo_success(client, mock_bingo_service):
    resp = await client.get("/api/v1/users/1/bingo?seed=2026-04")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["seed"] == "2026-04"
    assert len(data["cells"]) == 25
    assert data["total_completed"] == 1
    assert data["bingo_count"] == 0
    mock_bingo_service.get_user_bingo.assert_called_once()


@pytest.mark.asyncio
async def test_get_bingo_invalid_seed(client, mock_bingo_service):
    resp = await client.get("/api/v1/users/1/bingo?seed=invalid")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_bingo_missing_seed(client, mock_bingo_service):
    resp = await client.get("/api/v1/users/1/bingo")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_bingo_cached(client, mock_bingo_service, mock_cache_service):
    cached_data = {
        "user_id": 1,
        "seed": "2026-04",
        "cells": [
            {
                "index": i,
                "template": "free" if i == 12 else "genre",
                "label": "FREE" if i == 12 else f"A Genre{i} movie",
                "parameter": None if i == 12 else f"Genre{i}",
                "completed": i == 12,
                "movie_id": None,
            }
            for i in range(25)
        ],
        "completed_lines": [],
        "total_completed": 1,
        "bingo_count": 0,
    }
    mock_cache_service.get.return_value = json.dumps(cached_data)

    resp = await client.get("/api/v1/users/1/bingo?seed=2026-04")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["cells"]) == 25
    mock_bingo_service.get_user_bingo.assert_not_called()
