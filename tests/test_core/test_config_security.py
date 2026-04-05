"""Extensive tests for config security (Phase 3).

Verifies:
- SecretStr fields don't leak in repr/str
- Required secrets have no insecure defaults
- Security-related defaults are safe
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from cinematch.config import Settings, get_settings


class TestSecretStrFields:
    """Verify sensitive fields use SecretStr and don't leak values."""

    def test_database_url_is_secret_str(self):
        settings = get_settings()
        assert isinstance(settings.database_url, SecretStr)

    def test_database_url_sync_is_secret_str(self):
        settings = get_settings()
        assert isinstance(settings.database_url_sync, SecretStr)

    def test_redis_url_is_secret_str(self):
        settings = get_settings()
        assert isinstance(settings.redis_url, SecretStr)

    def test_secret_key_is_secret_str(self):
        settings = get_settings()
        assert isinstance(settings.secret_key, SecretStr)

    def test_secret_str_repr_hides_value(self):
        settings = get_settings()
        repr_str = repr(settings.database_url)
        assert "test" not in repr_str.lower() or "SecretStr" in repr_str

    def test_secret_str_str_hides_value(self):
        settings = get_settings()
        str_val = str(settings.database_url)
        # SecretStr.__str__ returns '**********'
        assert "**" in str_val

    def test_get_secret_value_returns_actual_value(self):
        settings = get_settings()
        actual = settings.database_url.get_secret_value()
        assert "postgresql" in actual


class TestSecurityDefaults:
    """Verify default values for security settings are safe."""

    def test_debug_defaults_to_false(self):
        field = Settings.model_fields["debug"]
        assert field.default is False

    def test_hsts_enabled_by_default(self):
        settings = get_settings()
        assert settings.hsts_enabled is True

    def test_rate_limiting_enabled_by_default(self):
        # Note: test env overrides this to False, but the Settings default is True
        s = Settings.model_fields["rate_limit_enabled"]
        assert s.default is True

    def test_jwt_algorithm_is_hs256(self):
        settings = get_settings()
        assert settings.jwt_algorithm == "HS256"

    def test_cors_origins_default_to_localhost(self):
        s = Settings.model_fields["cors_origins"]
        assert "http://localhost:3000" in s.default
        assert "http://localhost:5173" in s.default

    def test_cors_methods_no_wildcard(self):
        s = Settings.model_fields["cors_methods"]
        assert "*" not in s.default

    def test_cors_headers_no_wildcard(self):
        s = Settings.model_fields["cors_headers"]
        assert "*" not in s.default

    def test_cors_methods_include_options(self):
        s = Settings.model_fields["cors_methods"]
        assert "OPTIONS" in s.default

    def test_cors_headers_include_authorization(self):
        s = Settings.model_fields["cors_headers"]
        assert "Authorization" in s.default

    def test_statement_timeout_has_safe_default(self):
        s = Settings.model_fields["database_statement_timeout"]
        assert s.default == 30000  # 30 seconds

    def test_audit_logging_enabled_by_default(self):
        s = Settings.model_fields["audit_log_enabled"]
        assert s.default is True

    def test_pool_pre_ping_enabled_by_default(self):
        s = Settings.model_fields["db_pool_pre_ping"]
        assert s.default is True


class TestContentSecurityPolicy:
    """Verify CSP is restrictive."""

    def test_csp_default_includes_self(self):
        s = Settings.model_fields["content_security_policy"]
        assert "default-src 'self'" in s.default

    def test_csp_disallows_object_src(self):
        s = Settings.model_fields["content_security_policy"]
        assert "object-src 'none'" in s.default

    def test_csp_disallows_frame_ancestors(self):
        s = Settings.model_fields["content_security_policy"]
        assert "frame-ancestors 'none'" in s.default

    def test_csp_restricts_base_uri(self):
        s = Settings.model_fields["content_security_policy"]
        assert "base-uri 'self'" in s.default

    def test_csp_restricts_form_action(self):
        s = Settings.model_fields["content_security_policy"]
        assert "form-action 'self'" in s.default


class TestRateLimitDefaults:
    """Verify rate limit defaults are reasonable."""

    def test_auth_rate_limit_strict(self):
        s = Settings.model_fields["rate_limit_auth"]
        assert s.default == "5/minute"

    def test_recommendations_rate_limit(self):
        s = Settings.model_fields["rate_limit_recommendations"]
        assert s.default == "10/minute"

    def test_search_rate_limit(self):
        s = Settings.model_fields["rate_limit_search"]
        assert s.default == "30/minute"

    def test_csv_import_rate_limit(self):
        s = Settings.model_fields["rate_limit_csv_import"]
        assert s.default == "3/minute"

    def test_default_rate_limit(self):
        s = Settings.model_fields["rate_limit_default"]
        assert s.default == "100/minute"


class TestRequiredSecrets:
    """Verify that required secrets have no default values."""

    def test_database_url_is_required(self):
        field = Settings.model_fields["database_url"]
        assert field.default is None or field.is_required()

    def test_redis_url_is_required(self):
        field = Settings.model_fields["redis_url"]
        assert field.default is None or field.is_required()

    def test_secret_key_is_required(self):
        field = Settings.model_fields["secret_key"]
        assert field.default is None or field.is_required()

    def test_llm_api_key_is_optional(self):
        """LLM API key can be None (Ollama doesn't need one)."""
        field = Settings.model_fields["llm_api_key"]
        assert not field.is_required()


class TestImportExportLimits:
    """Verify data import/export bounds are set."""

    def test_import_max_rows_default(self):
        s = Settings.model_fields["import_max_rows"]
        assert s.default == 10_000

    def test_import_max_file_size_default(self):
        s = Settings.model_fields["import_max_file_size_mb"]
        assert s.default == 5
