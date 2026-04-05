"""Extensive tests for auth Pydantic schemas (RegisterRequest, LoginRequest, TokenResponse)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cinematch.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


# ---------------------------------------------------------------------------
# RegisterRequest validation
# ---------------------------------------------------------------------------
class TestRegisterRequest:
    def test_valid_registration(self):
        req = RegisterRequest(
            email="user@example.com",
            username="alice",
            password="secureP@ss1",
        )
        assert req.email == "user@example.com"
        assert req.username == "alice"
        assert req.password == "secureP@ss1"

    def test_email_min_length(self):
        # Min length is 5
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b", username="user", password="password1")

    def test_email_exactly_min_length(self):
        req = RegisterRequest(email="a@b.c", username="user", password="password1")
        assert req.email == "a@b.c"

    def test_email_max_length(self):
        # Max 320 characters
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a" * 316 + "@b.co",
                username="user",
                password="password1",
            )

    def test_email_at_max_length(self):
        email = "a" * 314 + "@b.com"  # 320 chars
        req = RegisterRequest(email=email, username="user", password="password1")
        assert len(req.email) == 320

    def test_username_min_length(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@test.com", username="ab", password="password1")

    def test_username_exactly_min_length(self):
        req = RegisterRequest(email="user@test.com", username="abc", password="password1")
        assert req.username == "abc"

    def test_username_max_length(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@test.com",
                username="a" * 51,
                password="password1",
            )

    def test_username_at_max_length(self):
        req = RegisterRequest(
            email="user@test.com",
            username="a" * 50,
            password="password1",
        )
        assert len(req.username) == 50

    def test_password_min_length(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@test.com", username="user", password="short")

    def test_password_exactly_min_length(self):
        req = RegisterRequest(email="user@test.com", username="user", password="a" * 8)
        assert len(req.password) == 8

    def test_password_max_length(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@test.com",
                username="user",
                password="a" * 129,
            )

    def test_password_at_max_length(self):
        req = RegisterRequest(
            email="user@test.com",
            username="user",
            password="a" * 128,
        )
        assert len(req.password) == 128

    def test_missing_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="user", password="password1")

    def test_missing_username(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@test.com", password="password1")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@test.com", username="user")

    def test_all_fields_missing(self):
        with pytest.raises(ValidationError):
            RegisterRequest()

    def test_empty_email_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="", username="user", password="password1")

    def test_empty_username_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@test.com", username="", password="password1")

    def test_empty_password_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@test.com", username="user", password="")

    def test_unicode_email_accepted(self):
        req = RegisterRequest(
            email="ü@example.com",
            username="user",
            password="password1",
        )
        assert "ü" in req.email

    def test_unicode_username_accepted(self):
        req = RegisterRequest(
            email="user@test.com",
            username="Ünser",
            password="password1",
        )
        assert req.username == "Ünser"

    def test_unicode_password_accepted(self):
        req = RegisterRequest(
            email="user@test.com",
            username="user",
            password="pässwörd1234",
        )
        assert "ö" in req.password


# ---------------------------------------------------------------------------
# LoginRequest validation
# ---------------------------------------------------------------------------
class TestLoginRequest:
    def test_valid_login(self):
        req = LoginRequest(email="user@test.com", password="password123")
        assert req.email == "user@test.com"

    def test_missing_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="password123")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="user@test.com")


# ---------------------------------------------------------------------------
# TokenResponse validation
# ---------------------------------------------------------------------------
class TestTokenResponse:
    def test_valid_token_response(self):
        resp = TokenResponse(
            access_token="eyJhbGciOiJ...",
            user_id=42,
            username="alice",
        )
        assert resp.access_token == "eyJhbGciOiJ..."
        assert resp.token_type == "bearer"
        assert resp.user_id == 42
        assert resp.username == "alice"

    def test_default_token_type(self):
        resp = TokenResponse(
            access_token="token",
            user_id=1,
            username="user",
        )
        assert resp.token_type == "bearer"

    def test_missing_access_token(self):
        with pytest.raises(ValidationError):
            TokenResponse(user_id=1, username="user")

    def test_missing_user_id(self):
        with pytest.raises(ValidationError):
            TokenResponse(access_token="token", username="user")

    def test_missing_username(self):
        with pytest.raises(ValidationError):
            TokenResponse(access_token="token", user_id=1)
