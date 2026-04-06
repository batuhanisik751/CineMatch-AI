"""Extensive tests for authentication API endpoints: register, login, /me."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cinematch.api.deps import get_audit_service, get_current_user, get_db
from cinematch.main import create_app
from cinematch.services.auth_service import hash_password


def _make_user(
    id: int = 1,
    email: str = "test@example.com",
    username: str = "testuser",
    hashed_password: str | None = None,
) -> MagicMock:
    u = MagicMock()
    u.id = id
    u.movielens_id = None
    u.email = email
    u.username = username
    u.hashed_password = hashed_password or hash_password("password123")
    u.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    return u


@pytest.fixture()
def mock_audit():
    svc = AsyncMock()
    svc.log.return_value = None
    return svc


@pytest.fixture()
def mock_db():
    return AsyncMock()


@pytest.fixture()
def auth_app(mock_audit, mock_db):
    """App WITHOUT get_current_user override — tests real auth flow."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_audit_service] = lambda: mock_audit
    return app


@pytest.fixture()
async def auth_client(auth_app):
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------
class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, auth_client, mock_db, mock_audit):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing user
        mock_db.execute.return_value = mock_result
        mock_db.refresh = AsyncMock(side_effect=lambda u: setattr(u, "id", 42))

        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": "new@test.com", "username": "newuser", "password": "strongpass1"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "newuser"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_client, mock_db):
        existing_user = _make_user(email="taken@test.com")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db.execute.return_value = mock_result

        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": "taken@test.com", "username": "newuser", "password": "strongpass1"},
        )
        assert resp.status_code == 409
        assert "Email already registered" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, auth_client, mock_db):
        # First call (email check) returns None, second (username check) returns existing
        existing_user = _make_user(username="taken")
        results = [MagicMock(), MagicMock()]
        results[0].scalar_one_or_none.return_value = None
        results[1].scalar_one_or_none.return_value = existing_user
        mock_db.execute = AsyncMock(side_effect=results)

        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": "new@test.com", "username": "taken", "password": "strongpass1"},
        )
        assert resp.status_code == 409
        assert "Username already taken" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_audits_event(self, auth_client, mock_db, mock_audit):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.refresh = AsyncMock(side_effect=lambda u: setattr(u, "id", 1))

        await auth_client.post(
            "/api/v1/auth/register",
            json={"email": "new@test.com", "username": "newuser", "password": "strongpass1"},
        )
        mock_audit.log.assert_awaited()
        call_args = mock_audit.log.call_args
        assert call_args[0][0] == "auth.register"

    @pytest.mark.asyncio
    async def test_register_email_too_short(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": "a@b", "username": "user", "password": "strongpass1"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_username_too_short(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": "valid@test.com", "username": "ab", "password": "strongpass1"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_password_too_short(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": "valid@test.com", "username": "validuser", "password": "short"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, auth_client):
        resp = await auth_client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_username_max_length(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@test.com",
                "username": "a" * 51,
                "password": "strongpass1",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_password_max_length(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@test.com",
                "username": "user",
                "password": "a" * 129,
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_email_max_length(self, auth_client):
        # RegisterRequest.email has max_length=320; 321 chars should fail
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": "a" * 317 + "@b.c",  # 321 chars
                "username": "user",
                "password": "strongpass1",
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------
class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, auth_client, mock_db, mock_audit):
        hashed = hash_password("password123")
        user = _make_user(id=5, email="user@test.com", hashed_password=hashed)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        resp = await auth_client.post(
            "/api/v1/auth/login",
            data={"username": "user@test.com", "password": "password123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"] == 5

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, auth_client, mock_db, mock_audit):
        hashed = hash_password("correct")
        user = _make_user(email="user@test.com", hashed_password=hashed)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        resp = await auth_client.post(
            "/api/v1/auth/login",
            data={"username": "user@test.com", "password": "wrong"},
        )
        assert resp.status_code == 401
        assert "Invalid email or password" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, auth_client, mock_db, mock_audit):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        resp = await auth_client.post(
            "/api/v1/auth/login",
            data={"username": "ghost@test.com", "password": "whatever"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_audits_success(self, auth_client, mock_db, mock_audit):
        hashed = hash_password("pass")
        user = _make_user(id=10, hashed_password=hashed)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        await auth_client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "pass"},
        )
        mock_audit.log.assert_awaited()
        call_args = mock_audit.log.call_args
        assert call_args[0][0] == "auth.login"

    @pytest.mark.asyncio
    async def test_login_audits_failure(self, auth_client, mock_db, mock_audit):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        await auth_client.post(
            "/api/v1/auth/login",
            data={"username": "bad@test.com", "password": "wrong"},
        )
        mock_audit.log.assert_awaited()
        call_args = mock_audit.log.call_args
        assert call_args[0][0] == "auth.login_failed"
        assert call_args.kwargs["status"] == "failure"

    @pytest.mark.asyncio
    async def test_login_returns_www_authenticate_header_on_failure(
        self, auth_client, mock_db, mock_audit
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        resp = await auth_client.post(
            "/api/v1/auth/login",
            data={"username": "bad@test.com", "password": "wrong"},
        )
        assert resp.headers.get("www-authenticate") == "Bearer"

    @pytest.mark.asyncio
    async def test_login_does_not_leak_user_existence(self, auth_client, mock_db, mock_audit):
        """Same error message whether user exists or not (prevents enumeration)."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        resp = await auth_client.post(
            "/api/v1/auth/login",
            data={"username": "nonexist@test.com", "password": "whatever"},
        )
        assert resp.json()["detail"] == "Invalid email or password"

    @pytest.mark.asyncio
    async def test_login_user_with_no_password(self, auth_client, mock_db, mock_audit):
        """Legacy users without password should fail login."""
        user = _make_user(hashed_password=None)
        user.hashed_password = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        resp = await auth_client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "anything"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------
class TestGetMe:
    @pytest.mark.asyncio
    async def test_me_returns_authenticated_user(self):
        user = _make_user(id=7, email="me@test.com", username="myself")
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 7
        assert data["email"] == "me@test.com"
        assert data["username"] == "myself"

    @pytest.mark.asyncio
    async def test_me_without_auth_returns_401(self):
        """No token = 401."""
        app = create_app()
        # No get_current_user override, and no DB override either
        # The endpoint should fail at the JWT level before hitting DB
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401
