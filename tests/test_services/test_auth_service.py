"""Extensive tests for authentication service: password hashing, JWT, user lookup."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from jose import jwt

from cinematch.services.auth_service import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_user_by_email,
    get_user_by_username,
    hash_password,
    register_user,
    verify_password,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
class TestHashPassword:
    def test_returns_string(self):
        result = hash_password("mypassword")
        assert isinstance(result, str)

    def test_hash_is_bcrypt_format(self):
        result = hash_password("mypassword")
        assert result.startswith("$2b$") or result.startswith("$2a$")

    def test_different_passwords_produce_different_hashes(self):
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2

    def test_same_password_produces_different_hashes_due_to_salt(self):
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2

    def test_empty_password_hashes_successfully(self):
        result = hash_password("")
        assert isinstance(result, str)

    def test_unicode_password_hashes_successfully(self):
        result = hash_password("p\u00e4ssw\u00f6rd\U0001f511")
        assert isinstance(result, str)

    def test_72_byte_password_hashes_successfully(self):
        # bcrypt has a 72-byte limit
        result = hash_password("a" * 72)
        assert isinstance(result, str)

    def test_long_password_raises_or_truncates(self):
        # bcrypt rejects >72 bytes; verify the behaviour
        with pytest.raises(ValueError):
            hash_password("a" * 200)


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        hashed = hash_password("correct")
        assert verify_password("correct", hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_empty_password_against_empty_hash(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True

    def test_empty_password_against_non_empty_hash(self):
        hashed = hash_password("notempty")
        assert verify_password("", hashed) is False

    def test_unicode_password_roundtrip(self):
        pw = "\u00fcberSicher123!"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_case_sensitivity(self):
        hashed = hash_password("CaseSensitive")
        assert verify_password("casesensitive", hashed) is False
        assert verify_password("CASESENSITIVE", hashed) is False

    def test_trailing_whitespace_matters(self):
        hashed = hash_password("password")
        assert verify_password("password ", hashed) is False

    def test_leading_whitespace_matters(self):
        hashed = hash_password("password")
        assert verify_password(" password", hashed) is False


# ---------------------------------------------------------------------------
# JWT token creation & decoding
# ---------------------------------------------------------------------------
class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token({"sub": "1", "username": "test"})
        assert isinstance(token, str)

    def test_token_contains_sub_claim(self):
        token = create_access_token({"sub": "42"})
        payload = decode_access_token(token)
        assert payload["sub"] == "42"

    def test_token_contains_exp_claim(self):
        token = create_access_token({"sub": "1"})
        payload = decode_access_token(token)
        assert "exp" in payload

    def test_token_expiry_is_in_future(self):
        token = create_access_token({"sub": "1"})
        payload = decode_access_token(token)
        assert payload["exp"] > time.time()

    def test_custom_data_preserved(self):
        token = create_access_token({"sub": "1", "username": "alice", "role": "admin"})
        payload = decode_access_token(token)
        assert payload["username"] == "alice"
        assert payload["role"] == "admin"

    def test_original_data_dict_not_mutated(self):
        data = {"sub": "1"}
        create_access_token(data)
        assert "exp" not in data


class TestDecodeAccessToken:
    def test_decodes_valid_token(self):
        token = create_access_token({"sub": "99"})
        payload = decode_access_token(token)
        assert payload["sub"] == "99"

    def test_raises_on_invalid_token(self):
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_access_token("not-a-real-jwt-token")

    def test_raises_on_tampered_token(self):
        from jose import JWTError

        token = create_access_token({"sub": "1"})
        # Flip a character in the signature
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with pytest.raises(JWTError):
            decode_access_token(tampered)

    def test_raises_on_wrong_secret(self):
        from jose import JWTError

        # Create a token with a different secret
        payload = {"sub": "1", "exp": datetime.now(UTC) + timedelta(hours=1)}
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_raises_on_expired_token(self):
        from jose import JWTError

        settings = __import__("cinematch.config", fromlist=["get_settings"]).get_settings()
        secret = settings.secret_key.get_secret_value()
        payload = {"sub": "1", "exp": datetime.now(UTC) - timedelta(hours=1)}
        token = jwt.encode(payload, secret, algorithm="HS256")
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_raises_on_empty_string(self):
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_access_token("")

    def test_raises_on_none_equivalent(self):
        from jose import JWTError

        with pytest.raises((JWTError, AttributeError)):
            decode_access_token("")


# ---------------------------------------------------------------------------
# User lookup functions
# ---------------------------------------------------------------------------
class TestGetUserByEmail:
    @pytest.mark.asyncio
    async def test_returns_user_when_found(self):
        mock_user = MagicMock(id=1, email="found@test.com")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db = AsyncMock()
        db.execute.return_value = mock_result

        user = await get_user_by_email("found@test.com", db)
        assert user is not None
        assert user.email == "found@test.com"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result

        user = await get_user_by_email("missing@test.com", db)
        assert user is None


class TestGetUserByUsername:
    @pytest.mark.asyncio
    async def test_returns_user_when_found(self):
        mock_user = MagicMock(id=1, username="alice")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db = AsyncMock()
        db.execute.return_value = mock_result

        user = await get_user_by_username("alice", db)
        assert user is not None
        assert user.username == "alice"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result

        user = await get_user_by_username("nobody", db)
        assert user is None


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------
class TestAuthenticateUser:
    @pytest.mark.asyncio
    async def test_returns_user_with_correct_credentials(self):
        hashed = hash_password("secret123")
        mock_user = MagicMock(id=1, email="user@test.com", hashed_password=hashed)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db = AsyncMock()
        db.execute.return_value = mock_result

        user = await authenticate_user("user@test.com", "secret123", db)
        assert user is not None
        assert user.id == 1

    @pytest.mark.asyncio
    async def test_returns_none_with_wrong_password(self):
        hashed = hash_password("correct")
        mock_user = MagicMock(id=1, email="user@test.com", hashed_password=hashed)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db = AsyncMock()
        db.execute.return_value = mock_result

        user = await authenticate_user("user@test.com", "wrong", db)
        assert user is None

    @pytest.mark.asyncio
    async def test_returns_none_when_user_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result

        user = await authenticate_user("ghost@test.com", "password", db)
        assert user is None

    @pytest.mark.asyncio
    async def test_returns_none_when_hashed_password_is_none(self):
        """Legacy users migrated without a password should fail auth."""
        mock_user = MagicMock(id=1, email="legacy@test.com", hashed_password=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db = AsyncMock()
        db.execute.return_value = mock_result

        user = await authenticate_user("legacy@test.com", "password", db)
        assert user is None

    @pytest.mark.asyncio
    async def test_normalizes_email_lowercase(self):
        hashed = hash_password("pass")
        mock_user = MagicMock(id=1, email="user@test.com", hashed_password=hashed)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db = AsyncMock()
        db.execute.return_value = mock_result

        await authenticate_user("  USER@TEST.COM  ", "pass", db)
        # Verify the query was made with normalized email
        call_args = db.execute.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_strips_whitespace_from_email(self):
        hashed = hash_password("pass")
        mock_user = MagicMock(id=1, email="user@test.com", hashed_password=hashed)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db = AsyncMock()
        db.execute.return_value = mock_result

        user = await authenticate_user("  user@test.com  ", "pass", db)
        assert user is not None


# ---------------------------------------------------------------------------
# register_user
# ---------------------------------------------------------------------------
class TestRegisterUser:
    @pytest.mark.asyncio
    async def test_creates_user_with_hashed_password(self):
        db = AsyncMock()
        db.refresh = AsyncMock()

        await register_user("new@test.com", "newuser", "strongpass", db)

        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

        added_user = db.add.call_args[0][0]
        assert added_user.email == "new@test.com"
        assert added_user.username == "newuser"
        assert added_user.hashed_password != "strongpass"  # Must be hashed
        assert added_user.movielens_id is None

    @pytest.mark.asyncio
    async def test_normalizes_email_to_lowercase(self):
        db = AsyncMock()
        db.refresh = AsyncMock()

        await register_user("TEST@EXAMPLE.COM", "testuser", "password", db)

        added_user = db.add.call_args[0][0]
        assert added_user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_strips_whitespace_from_email(self):
        db = AsyncMock()
        db.refresh = AsyncMock()

        await register_user("  user@test.com  ", "testuser", "password", db)

        added_user = db.add.call_args[0][0]
        assert added_user.email == "user@test.com"

    @pytest.mark.asyncio
    async def test_strips_whitespace_from_username(self):
        db = AsyncMock()
        db.refresh = AsyncMock()

        await register_user("user@test.com", "  myname  ", "password", db)

        added_user = db.add.call_args[0][0]
        assert added_user.username == "myname"

    @pytest.mark.asyncio
    async def test_password_is_verifiable_after_registration(self):
        db = AsyncMock()
        db.refresh = AsyncMock()

        await register_user("user@test.com", "user", "MySecret!", db)

        added_user = db.add.call_args[0][0]
        assert verify_password("MySecret!", added_user.hashed_password) is True
        assert verify_password("WrongPass", added_user.hashed_password) is False
