"""Tests: docs/debug endpoints disabled in production, enabled in debug mode."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from cinematch.main import create_app


@pytest.mark.asyncio
async def test_health_endpoint_returns_debug_field(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "debug" in body
    assert isinstance(body["debug"], bool)


@pytest.mark.asyncio
async def test_health_debug_false_by_default(client):
    resp = await client.get("/health")
    body = resp.json()
    assert body["debug"] is False


@pytest.mark.asyncio
async def test_docs_disabled_when_debug_false(client):
    resp = await client.get("/docs")
    assert resp.status_code == 404

    resp = await client.get("/redoc")
    assert resp.status_code == 404

    resp = await client.get("/openapi.json")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_docs_enabled_when_debug_true():
    with patch.dict("os.environ", {"CINEMATCH_DEBUG": "true"}):
        from cinematch.config import Settings

        debug_settings = Settings(
            database_url="postgresql+asyncpg://test:test@localhost:5432/test",
            database_url_sync="postgresql://test:test@localhost:5432/test",
            redis_url="redis://localhost:6379/0",
            secret_key="test-secret-key-not-for-production",
            rate_limit_enabled=False,
            debug=True,
        )

        with patch("cinematch.main.get_settings", return_value=debug_settings):
            debug_app = create_app()

        transport = ASGITransport(app=debug_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/docs")
            assert resp.status_code == 200

            resp = await ac.get("/redoc")
            assert resp.status_code == 200

            resp = await ac.get("/openapi.json")
            assert resp.status_code == 200

            resp = await ac.get("/health")
            body = resp.json()
            assert body["debug"] is True
