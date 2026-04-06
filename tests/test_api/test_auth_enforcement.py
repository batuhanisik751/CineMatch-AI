"""Tests that protected endpoints enforce authentication and authorization.

Verifies:
- Endpoints return 401 when no token is provided
- Endpoints return 403 when accessing another user's resources (IDOR protection)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cinematch.api.deps import (
    get_audit_service,
    get_cache_service,
    get_content_recommender,
    get_current_user,
    get_db,
    get_dismissal_service,
    get_hybrid_recommender,
    get_movie_service,
    get_rating_service,
    get_user_list_service,
    get_user_stats_service,
    get_watchlist_service,
)
from cinematch.main import create_app


def _make_user(id: int = 1) -> MagicMock:
    u = MagicMock()
    u.id = id
    u.movielens_id = id
    u.email = f"user{id}@test.com"
    u.username = f"user{id}"
    u.hashed_password = "hashed"
    u.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    return u


# ---------------------------------------------------------------------------
# 401 tests — no token provided
# ---------------------------------------------------------------------------
class TestEndpointsReturn401WithoutAuth:
    """All protected endpoints must return 401 when no Authorization header is sent."""

    @pytest.fixture()
    def unauthenticated_app(self):
        """App without get_current_user override — forces real auth."""
        app = create_app()
        return app

    @pytest.fixture()
    async def client(self, unauthenticated_app):
        transport = ASGITransport(app=unauthenticated_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_ratings_list_requires_auth(self, client):
        resp = await client.get("/api/v1/users/1/ratings")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_ratings_import_requires_auth(self, client):
        resp = await client.post("/api/v1/users/1/ratings/import")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_ratings_export_requires_auth(self, client):
        resp = await client.get("/api/v1/users/1/ratings/export")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_ratings_check_requires_auth(self, client):
        resp = await client.get("/api/v1/users/1/ratings/check?movie_ids=1,2,3")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_rate_movie_requires_auth(self, client):
        resp = await client.post(
            "/api/v1/users/1/ratings",
            json={"movie_id": 1, "rating": 8},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_recommendations_requires_auth(self, client):
        resp = await client.get("/api/v1/users/1/recommendations")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_watchlist_requires_auth(self, client):
        resp = await client.get("/api/v1/users/1/watchlist")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_dismissals_requires_auth(self, client):
        resp = await client.get("/api/v1/users/1/dismissals")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_lists_requires_auth(self, client):
        resp = await client.get("/api/v1/users/1/lists")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_audit_logs_requires_auth(self, client):
        resp = await client.get("/api/v1/users/audit-logs")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_pickle_safety_requires_auth(self, client):
        resp = await client.get("/api/v1/system/pickle-safety")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_db_security_requires_auth(self, client):
        resp = await client.get("/api/v1/system/db-security")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_dep_scan_requires_auth(self, client):
        resp = await client.get("/api/v1/system/dep-scan")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_container_security_requires_auth(self, client):
        resp = await client.get("/api/v1/system/container-security")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_me_requires_auth(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 403 tests — accessing another user's resources
# ---------------------------------------------------------------------------
class TestEndpointsReturn403ForOtherUser:
    """Endpoints with require_same_user must return 403 when user_id != current_user.id."""

    @pytest.fixture()
    def app_as_user_1(self):
        """App authenticated as user 1."""
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: _make_user(id=1)
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        mock_rating_service = AsyncMock()
        mock_rating_service.get_user_ratings.return_value = ([], 0)
        mock_rating_service.get_ratings_for_movies.return_value = {}
        app.dependency_overrides[get_rating_service] = lambda: mock_rating_service

        mock_movie_service = AsyncMock()
        app.dependency_overrides[get_movie_service] = lambda: mock_movie_service

        mock_watchlist_service = AsyncMock()
        mock_watchlist_service.get_user_watchlist.return_value = ([], 0)
        app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

        mock_dismissal_service = AsyncMock()
        mock_dismissal_service.get_user_dismissals.return_value = ([], 0)
        app.dependency_overrides[get_dismissal_service] = lambda: mock_dismissal_service

        mock_list_service = AsyncMock()
        mock_list_service.get_user_lists.return_value = ([], 0)
        app.dependency_overrides[get_user_list_service] = lambda: mock_list_service

        mock_user_stats = AsyncMock()
        app.dependency_overrides[get_user_stats_service] = lambda: mock_user_stats

        mock_hybrid = AsyncMock()
        app.dependency_overrides[get_hybrid_recommender] = lambda: mock_hybrid

        mock_content = AsyncMock()
        app.dependency_overrides[get_content_recommender] = lambda: mock_content

        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        app.dependency_overrides[get_cache_service] = lambda: mock_cache

        mock_audit = AsyncMock()
        mock_audit.log.return_value = None
        app.dependency_overrides[get_audit_service] = lambda: mock_audit

        return app

    @pytest.fixture()
    async def client(self, app_as_user_1):
        transport = ASGITransport(app=app_as_user_1)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_ratings_list_403_for_other_user(self, client):
        resp = await client.get("/api/v1/users/999/ratings")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_ratings_export_403_for_other_user(self, client):
        resp = await client.get("/api/v1/users/999/ratings/export")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_ratings_check_403_for_other_user(self, client):
        resp = await client.get("/api/v1/users/999/ratings/check?movie_ids=1")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_rate_movie_403_for_other_user(self, client):
        resp = await client.post(
            "/api/v1/users/999/ratings",
            json={"movie_id": 1, "rating": 8},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_watchlist_403_for_other_user(self, client):
        resp = await client.get("/api/v1/users/999/watchlist")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_dismissals_403_for_other_user(self, client):
        resp = await client.get("/api/v1/users/999/dismissals")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_lists_403_for_other_user(self, client):
        resp = await client.get("/api/v1/users/999/lists")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_recommendations_403_for_other_user(self, client):
        resp = await client.get("/api/v1/users/999/recommendations")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_own_resources_allowed(self, client):
        """User 1 can access their own resources (not 403)."""
        resp = await client.get("/api/v1/users/1/ratings")
        assert resp.status_code != 403

    @pytest.mark.asyncio
    async def test_idor_prevention_on_post_rating(self, client):
        """Cannot submit a rating as another user."""
        resp = await client.post(
            "/api/v1/users/2/ratings",
            json={"movie_id": 1, "rating": 8},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_idor_prevention_on_watchlist_add(self, client):
        resp = await client.post(
            "/api/v1/users/2/watchlist",
            json={"movie_id": 1},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_idor_prevention_on_dismissal_add(self, client):
        resp = await client.post(
            "/api/v1/users/2/dismissals",
            json={"movie_id": 1},
        )
        assert resp.status_code == 403
