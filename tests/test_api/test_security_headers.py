"""Integration tests: security headers on real API responses."""

from __future__ import annotations

import pytest

EXPECTED_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


@pytest.mark.asyncio
async def test_health_endpoint_has_security_headers(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    for header, value in EXPECTED_HEADERS.items():
        assert resp.headers[header] == value
    assert "Content-Security-Policy" in resp.headers
    assert "default-src 'self'" in resp.headers["Content-Security-Policy"]


@pytest.mark.asyncio
async def test_api_endpoint_has_security_headers(client):
    resp = await client.get("/api/v1/movies/1")
    assert resp.status_code == 200
    for header, value in EXPECTED_HEADERS.items():
        assert resp.headers[header] == value
