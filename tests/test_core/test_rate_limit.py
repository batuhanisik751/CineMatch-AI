"""Tests for rate limiting helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cinematch.core.rate_limit import get_user_or_ip, limiter


@pytest.fixture()
def mock_request():
    """Create a mock Starlette Request."""
    request = MagicMock()
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "192.168.1.100"
    request.scope = {"type": "http"}
    return request


class TestGetUserOrIp:
    """Tests for the get_user_or_ip key function."""

    def test_returns_ip_when_no_auth_header(self, mock_request):
        mock_request.headers = {}
        with patch(
            "cinematch.core.rate_limit.get_remote_address",
            return_value="192.168.1.100",
        ):
            result = get_user_or_ip(mock_request)
        assert result == "192.168.1.100"

    def test_returns_ip_when_auth_header_not_bearer(self, mock_request):
        mock_request.headers = {"Authorization": "Basic abc123"}
        with patch(
            "cinematch.core.rate_limit.get_remote_address",
            return_value="192.168.1.100",
        ):
            result = get_user_or_ip(mock_request)
        assert result == "192.168.1.100"

    def test_returns_user_id_when_valid_bearer_token(self, mock_request):
        mock_request.headers = {"Authorization": "Bearer valid-token"}
        with patch(
            "cinematch.services.auth_service.decode_access_token",
            return_value={"sub": "42"},
        ):
            result = get_user_or_ip(mock_request)
        assert result == "user:42"

    def test_returns_ip_when_token_decode_fails(self, mock_request):
        mock_request.headers = {"Authorization": "Bearer bad-token"}
        with (
            patch(
                "cinematch.services.auth_service.decode_access_token",
                side_effect=Exception("Invalid token"),
            ),
            patch(
                "cinematch.core.rate_limit.get_remote_address",
                return_value="10.0.0.1",
            ),
        ):
            result = get_user_or_ip(mock_request)
        assert result == "10.0.0.1"

    def test_returns_ip_when_token_has_no_sub(self, mock_request):
        mock_request.headers = {"Authorization": "Bearer token-no-sub"}
        with (
            patch(
                "cinematch.services.auth_service.decode_access_token",
                return_value={"exp": 9999999999},
            ),
            patch(
                "cinematch.core.rate_limit.get_remote_address",
                return_value="10.0.0.1",
            ),
        ):
            result = get_user_or_ip(mock_request)
        assert result == "10.0.0.1"


class TestLimiterConfig:
    """Tests for limiter configuration."""

    def test_limiter_is_disabled_in_test_env(self):
        assert limiter.enabled is False

    def test_limiter_has_default_limits(self):
        assert len(limiter._default_limits) > 0
