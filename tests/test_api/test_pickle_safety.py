"""Tests for the pickle safety status endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from cinematch.api.deps import get_current_user
from cinematch.main import create_app


def _make_user(id: int = 1):
    u = MagicMock()
    u.id = id
    u.email = "test@example.com"
    u.username = "testuser"
    return u


def _make_artifacts(statuses: list[str]) -> list[dict]:
    names = [
        "faiss_id_map.pkl",
        "als_model.pkl",
        "als_user_map.pkl",
        "als_item_map.pkl",
    ]
    return [
        {
            "file_name": names[i],
            "file_path": f"data/processed/{names[i]}",
            "expected_hash": "a" * 64 if s == "verified" else None,
            "actual_hash": "a" * 64 if s != "missing_artifact" else None,
            "status": s,
            "file_size_bytes": 1024 if s != "missing_artifact" else None,
            "last_modified": datetime.now(UTC) if s != "missing_artifact" else None,
        }
        for i, s in enumerate(statuses)
    ]


@pytest.fixture()
def pickle_safety_app():
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    return app


@pytest.fixture()
async def pickle_safety_client(pickle_safety_app):
    transport = ASGITransport(app=pickle_safety_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_pickle_safety_returns_expected_shape(pickle_safety_client):
    artifacts = _make_artifacts(["verified"] * 4)
    with patch(
        "cinematch.api.v1.pickle_safety.get_all_artifact_statuses",
        return_value=artifacts,
    ):
        resp = await pickle_safety_client.get("/api/v1/system/pickle-safety")
    assert resp.status_code == 200
    data = resp.json()
    assert "artifacts" in data
    assert "all_verified" in data
    assert "checked_at" in data
    assert len(data["artifacts"]) == 4


@pytest.mark.asyncio
async def test_pickle_safety_all_verified(pickle_safety_client):
    artifacts = _make_artifacts(["verified"] * 4)
    with patch(
        "cinematch.api.v1.pickle_safety.get_all_artifact_statuses",
        return_value=artifacts,
    ):
        resp = await pickle_safety_client.get("/api/v1/system/pickle-safety")
    assert resp.json()["all_verified"] is True


@pytest.mark.asyncio
async def test_pickle_safety_mismatch_detected(pickle_safety_client):
    artifacts = _make_artifacts(["verified", "mismatch", "verified", "verified"])
    with patch(
        "cinematch.api.v1.pickle_safety.get_all_artifact_statuses",
        return_value=artifacts,
    ):
        resp = await pickle_safety_client.get("/api/v1/system/pickle-safety")
    data = resp.json()
    assert data["all_verified"] is False
    assert data["artifacts"][1]["status"] == "mismatch"


@pytest.mark.asyncio
async def test_pickle_safety_requires_auth():
    app = create_app()
    # Don't override get_current_user — endpoint should require auth
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/system/pickle-safety")
    assert resp.status_code == 401
