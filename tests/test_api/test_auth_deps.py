"""Extensive tests for auth dependencies: get_current_user, require_same_user."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from cinematch.api.deps import get_current_user, require_same_user
from cinematch.services.auth_service import create_access_token


def _make_user(id: int = 1) -> MagicMock:
    u = MagicMock()
    u.id = id
    u.email = f"user{id}@test.com"
    u.username = f"user{id}"
    u.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    return u


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------
class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_returns_user_for_valid_token(self):
        token = create_access_token({"sub": "42", "username": "alice"})
        mock_user = _make_user(id=42)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db = AsyncMock()
        db.execute.return_value = mock_result

        user = await get_current_user(token=token, db=db)
        assert user.id == 42

    @pytest.mark.asyncio
    async def test_raises_401_for_invalid_token(self):
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="not.a.valid.jwt", db=db)
        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_401_for_expired_token(self):
        settings = __import__("cinematch.config", fromlist=["get_settings"]).get_settings()
        secret = settings.secret_key.get_secret_value()
        payload = {"sub": "1", "exp": datetime.now(UTC) - timedelta(hours=1)}
        token = jwt.encode(payload, secret, algorithm="HS256")

        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_when_sub_is_missing(self):
        settings = __import__("cinematch.config", fromlist=["get_settings"]).get_settings()
        secret = settings.secret_key.get_secret_value()
        payload = {"exp": datetime.now(UTC) + timedelta(hours=1)}
        token = jwt.encode(payload, secret, algorithm="HS256")

        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_when_user_not_found_in_db(self):
        token = create_access_token({"sub": "999"})
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_for_empty_token(self):
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="", db=db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_for_wrong_algorithm_token(self):
        settings = __import__("cinematch.config", fromlist=["get_settings"]).get_settings()
        secret = settings.secret_key.get_secret_value()
        payload = {"sub": "1", "exp": datetime.now(UTC) + timedelta(hours=1)}
        # Encode with HS384 instead of HS256
        token = jwt.encode(payload, secret, algorithm="HS384")

        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_www_authenticate_header_in_401(self):
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="bad", db=db)
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.asyncio
    async def test_sub_converted_to_int_for_db_lookup(self):
        token = create_access_token({"sub": "7"})
        mock_user = _make_user(id=7)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db = AsyncMock()
        db.execute.return_value = mock_result

        user = await get_current_user(token=token, db=db)
        assert user.id == 7
        db.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# require_same_user
# ---------------------------------------------------------------------------
class TestRequireSameUser:
    def test_does_nothing_when_ids_match(self):
        require_same_user(1, 1)  # Should not raise

    def test_raises_403_when_ids_differ(self):
        with pytest.raises(HTTPException) as exc_info:
            require_same_user(1, 2)
        assert exc_info.value.status_code == 403
        assert "Not authorized" in exc_info.value.detail

    def test_raises_403_for_large_id_mismatch(self):
        with pytest.raises(HTTPException) as exc_info:
            require_same_user(100, 999999)
        assert exc_info.value.status_code == 403

    def test_zero_ids_match(self):
        require_same_user(0, 0)  # Should not raise

    def test_negative_ids_still_enforce(self):
        with pytest.raises(HTTPException) as exc_info:
            require_same_user(-1, 1)
        assert exc_info.value.status_code == 403
