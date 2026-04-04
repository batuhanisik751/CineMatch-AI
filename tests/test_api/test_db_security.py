"""Tests for the database security status endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cinematch.api.deps import get_current_user, get_db
from cinematch.main import create_app


def _make_user(id: int = 1):
    u = MagicMock()
    u.id = id
    u.email = "test@example.com"
    u.username = "testuser"
    return u


def _mock_db_session():
    """Create a mock db session with pg_stat_ssl, SHOW, and current_user."""
    db = AsyncMock()

    def _execute_side_effect(stmt):
        query = str(stmt.text) if hasattr(stmt, "text") else str(stmt)
        result = MagicMock()
        if "pg_stat_ssl" in query:
            result.first.return_value = (False, None)
        elif "statement_timeout" in query.lower():
            result.first.return_value = ("30s",)
        elif "current_user" in query.lower():
            result.first.return_value = ("cinematch", "cinematch")
        else:
            result.first.return_value = None
        return result

    db.execute = AsyncMock(side_effect=_execute_side_effect)
    return db


@pytest.fixture()
def db_security_app():
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    app.dependency_overrides[get_db] = lambda: _mock_db_session()
    return app


@pytest.fixture()
async def db_security_client(db_security_app):
    transport = ASGITransport(app=db_security_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_db_security_returns_expected_shape(db_security_client):
    resp = await db_security_client.get("/api/v1/system/db-security")
    assert resp.status_code == 200
    data = resp.json()
    assert "ssl" in data
    assert "statement_timeout" in data
    assert "connection" in data
    assert "pool" in data

    assert data["ssl"]["configured_mode"] == "disable"
    assert data["ssl"]["active"] is False

    assert data["statement_timeout"]["configured_ms"] == 0
    assert data["statement_timeout"]["active"] == "30s"

    assert data["connection"]["current_user"] == "cinematch"
    assert data["connection"]["current_database"] == "cinematch"

    assert isinstance(data["pool"]["size"], int)
    assert isinstance(data["pool"]["pool_pre_ping"], bool)


@pytest.mark.asyncio
async def test_db_security_requires_auth():
    app = create_app()
    # Don't override get_current_user — endpoint should require auth
    app.dependency_overrides[get_db] = lambda: _mock_db_session()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/system/db-security")
    assert resp.status_code == 401
