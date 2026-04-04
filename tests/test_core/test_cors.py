"""Tests for CORS production configuration."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

ALLOWED_ORIGIN = "http://localhost:3000"
DISALLOWED_ORIGIN = "http://evil.com"
ALLOWED_METHODS = ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
ALLOWED_HEADERS = ["Content-Type", "Authorization"]


def _homepage(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _make_app() -> Starlette:
    app = Starlette(routes=[Route("/", _homepage)])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ALLOWED_ORIGIN],
        allow_credentials=True,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
    )
    return app


@pytest.fixture()
def client():
    return TestClient(_make_app())


class TestPreflightAllowedOrigin:
    """Preflight from an allowed origin returns correct CORS headers."""

    def test_preflight_returns_allow_origin(self, client):
        resp = client.options(
            "/",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN

    def test_preflight_returns_allow_methods(self, client):
        resp = client.options(
            "/",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        allowed = resp.headers["Access-Control-Allow-Methods"]
        for method in ["GET", "POST", "PATCH", "PUT", "DELETE"]:
            assert method in allowed

    def test_preflight_returns_allow_headers(self, client):
        resp = client.options(
            "/",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type, Authorization",
            },
        )
        allowed = resp.headers["Access-Control-Allow-Headers"]
        assert "Content-Type" in allowed or "content-type" in allowed
        assert "Authorization" in allowed or "authorization" in allowed

    def test_preflight_returns_allow_credentials(self, client):
        resp = client.options(
            "/",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers["Access-Control-Allow-Credentials"] == "true"


class TestPreflightDisallowedOrigin:
    """Preflight from a disallowed origin is rejected."""

    def test_disallowed_origin_no_allow_header(self, client):
        resp = client.options(
            "/",
            headers={
                "Origin": DISALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "Access-Control-Allow-Origin" not in resp.headers


class TestPreflightDisallowedMethod:
    """Preflight requesting a disallowed method is rejected."""

    def test_trace_method_not_allowed(self, client):
        resp = client.options(
            "/",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "TRACE",
            },
        )
        allow_methods = resp.headers.get("Access-Control-Allow-Methods", "")
        assert "TRACE" not in allow_methods


class TestPreflightDisallowedHeader:
    """Preflight requesting a disallowed header is rejected."""

    def test_custom_header_not_allowed(self, client):
        resp = client.options(
            "/",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Evil-Header",
            },
        )
        # Starlette responds 400 for disallowed headers in preflight
        assert resp.status_code == 400 or "X-Evil-Header" not in resp.headers.get(
            "Access-Control-Allow-Headers", ""
        )


class TestSimpleRequest:
    """Simple cross-origin GET includes CORS headers."""

    def test_allowed_origin_get(self, client):
        resp = client.get("/", headers={"Origin": ALLOWED_ORIGIN})
        assert resp.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN

    def test_disallowed_origin_get(self, client):
        resp = client.get("/", headers={"Origin": DISALLOWED_ORIGIN})
        assert "Access-Control-Allow-Origin" not in resp.headers


class TestSettingsIntegration:
    """Verify create_app wires CORS settings from config."""

    def test_app_uses_settings_cors_values(self):
        with patch("cinematch.main.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.cors_origins = ["http://test.example.com"]
            settings.cors_methods = ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
            settings.cors_headers = ["Content-Type", "Authorization"]
            settings.cors_allow_credentials = True
            settings.debug = False
            settings.hsts_enabled = False
            settings.content_security_policy = "default-src 'self'"
            settings.rate_limit_enabled = False
            settings.rate_limit_default = "100/minute"
            settings.rate_limit_auth = "5/minute"
            settings.rate_limit_recommendations = "10/minute"
            settings.rate_limit_search = "30/minute"

            from cinematch.main import create_app

            app = create_app()
            client = TestClient(app, raise_server_exceptions=False)

            resp = client.options(
                "/api/v1/movies/search",
                headers={
                    "Origin": "http://test.example.com",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert resp.headers.get("Access-Control-Allow-Origin") == "http://test.example.com"
