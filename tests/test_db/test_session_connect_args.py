"""Tests for _build_connect_args in session.py."""

from __future__ import annotations

import ssl
from unittest.mock import patch


def _build_with_overrides(**overrides):
    """Call _build_connect_args with patched settings."""
    defaults = {
        "database_ssl_mode": "disable",
        "database_statement_timeout": 0,
    }
    defaults.update(overrides)

    with patch("cinematch.db.session.settings") as mock_settings:
        for key, val in defaults.items():
            setattr(mock_settings, key, val)

        from cinematch.db.session import _build_connect_args

        return _build_connect_args()


class TestSSLModes:
    def test_disable_has_no_ssl_key(self):
        args = _build_with_overrides(database_ssl_mode="disable")
        assert "ssl" not in args

    def test_prefer_passes_string(self):
        args = _build_with_overrides(database_ssl_mode="prefer")
        assert args["ssl"] == "prefer"

    def test_require_creates_ssl_context_no_verify(self):
        args = _build_with_overrides(database_ssl_mode="require")
        ctx = args["ssl"]
        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.verify_mode == ssl.CERT_NONE
        assert ctx.check_hostname is False

    def test_verify_ca_creates_ssl_context_with_cert_check(self):
        args = _build_with_overrides(database_ssl_mode="verify-ca")
        ctx = args["ssl"]
        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.check_hostname is False
        assert ctx.verify_mode != ssl.CERT_NONE

    def test_verify_full_creates_ssl_context_with_hostname_check(self):
        args = _build_with_overrides(database_ssl_mode="verify-full")
        ctx = args["ssl"]
        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.check_hostname is True


class TestStatementTimeout:
    def test_zero_timeout_omits_server_settings(self):
        args = _build_with_overrides(database_statement_timeout=0)
        assert "server_settings" not in args

    def test_positive_timeout_sets_server_settings(self):
        args = _build_with_overrides(database_statement_timeout=30000)
        assert args["server_settings"]["statement_timeout"] == "30000"

    def test_custom_timeout_value(self):
        args = _build_with_overrides(database_statement_timeout=5000)
        assert args["server_settings"]["statement_timeout"] == "5000"


class TestCombined:
    def test_ssl_and_timeout_together(self):
        args = _build_with_overrides(
            database_ssl_mode="require",
            database_statement_timeout=15000,
        )
        assert isinstance(args["ssl"], ssl.SSLContext)
        assert args["server_settings"]["statement_timeout"] == "15000"
