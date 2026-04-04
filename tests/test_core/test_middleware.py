"""Tests for security headers middleware."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from cinematch.core.middleware import SecurityHeadersMiddleware


def _homepage(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _make_app() -> Starlette:
    app = Starlette(routes=[Route("/", _homepage)])
    app.add_middleware(SecurityHeadersMiddleware)
    return app


@pytest.fixture()
def client():
    return TestClient(_make_app())


@pytest.fixture()
def response(client):
    return client.get("/")


class TestStaticHeaders:
    """All five static headers must appear on every response."""

    def test_x_content_type_options(self, response):
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self, response):
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_referrer_policy(self, response):
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, response):
        assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"

    def test_content_security_policy(self, response):
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "https://fonts.googleapis.com" in csp
        assert "https://fonts.gstatic.com" in csp
        assert "https://image.tmdb.org" in csp
        assert "frame-ancestors 'none'" in csp


class TestHSTS:
    """HSTS is conditional on debug mode."""

    def test_hsts_present_when_production(self, response):
        # Default settings: debug=False, hsts_enabled=True
        assert "Strict-Transport-Security" in response.headers
        assert "max-age=63072000" in response.headers["Strict-Transport-Security"]
        assert "includeSubDomains" in response.headers["Strict-Transport-Security"]

    def test_hsts_absent_when_debug(self):
        app = _make_app()
        client = TestClient(app)
        with patch("cinematch.core.middleware.get_settings") as mock_settings:
            mock_settings.return_value.debug = True
            mock_settings.return_value.hsts_enabled = True
            mock_settings.return_value.content_security_policy = "default-src 'self'"
            resp = client.get("/")
        assert "Strict-Transport-Security" not in resp.headers

    def test_hsts_absent_when_disabled(self):
        app = _make_app()
        client = TestClient(app)
        with patch("cinematch.core.middleware.get_settings") as mock_settings:
            mock_settings.return_value.debug = False
            mock_settings.return_value.hsts_enabled = False
            mock_settings.return_value.content_security_policy = "default-src 'self'"
            resp = client.get("/")
        assert "Strict-Transport-Security" not in resp.headers
