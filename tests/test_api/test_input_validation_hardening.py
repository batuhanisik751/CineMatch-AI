"""Extensive tests for input validation hardening (Phase 5).

Covers:
- Bulk check movie IDs cap (200 max)
- Search query max_length enforcement
- Pagination bounds
- Non-integer movie_ids rejection
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cinematch.api.deps import (
    get_cache_service,
    get_current_user,
    get_db,
    get_dismissal_service,
    get_embedding_service,
    get_movie_service,
    get_rating_service,
    get_watchlist_service,
    get_audit_service,
)
from cinematch.main import create_app


def _make_user(id: int = 1) -> MagicMock:
    u = MagicMock()
    u.id = id
    u.movielens_id = id
    u.email = "test@example.com"
    u.username = "testuser"
    u.hashed_password = "hashed"
    u.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    return u


@pytest.fixture()
def mock_services():
    movie_svc = AsyncMock()
    movie_svc.search_by_title.return_value = ([], 0)
    movie_svc.semantic_search.return_value = []
    movie_svc.get_autocomplete.return_value = []

    rating_svc = AsyncMock()
    rating_svc.bulk_check.return_value = {}
    rating_svc.get_user_ratings.return_value = ([], 0)
    rating_svc.get_ratings_for_movies.return_value = {}

    watchlist_svc = AsyncMock()
    watchlist_svc.bulk_check.return_value = {}

    dismissal_svc = AsyncMock()
    dismissal_svc.bulk_check.return_value = {}

    cache_svc = AsyncMock()
    cache_svc.get.return_value = None

    embedding_svc = MagicMock()
    embedding_svc.encode.return_value = [0.1] * 384

    audit_svc = AsyncMock()
    audit_svc.log.return_value = None

    return {
        "movie": movie_svc,
        "rating": rating_svc,
        "watchlist": watchlist_svc,
        "dismissal": dismissal_svc,
        "cache": cache_svc,
        "embedding": embedding_svc,
        "audit": audit_svc,
    }


@pytest.fixture()
def app(mock_services):
    test_app = create_app()
    test_app.dependency_overrides[get_current_user] = lambda: _make_user(id=1)
    test_app.dependency_overrides[get_db] = lambda: AsyncMock()
    test_app.dependency_overrides[get_movie_service] = lambda: mock_services["movie"]
    test_app.dependency_overrides[get_rating_service] = lambda: mock_services["rating"]
    test_app.dependency_overrides[get_watchlist_service] = lambda: mock_services["watchlist"]
    test_app.dependency_overrides[get_dismissal_service] = lambda: mock_services["dismissal"]
    test_app.dependency_overrides[get_cache_service] = lambda: mock_services["cache"]
    test_app.dependency_overrides[get_embedding_service] = lambda: mock_services["embedding"]
    test_app.dependency_overrides[get_audit_service] = lambda: mock_services["audit"]
    return test_app


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Bulk check movie IDs cap
# ---------------------------------------------------------------------------
class TestBulkCheckIdsCap:
    @pytest.mark.asyncio
    async def test_exactly_200_ids_allowed(self, client):
        ids = ",".join(str(i) for i in range(1, 201))
        resp = await client.get(f"/api/v1/users/1/ratings/check?movie_ids={ids}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_201_ids_rejected(self, client):
        ids = ",".join(str(i) for i in range(1, 202))
        resp = await client.get(f"/api/v1/users/1/ratings/check?movie_ids={ids}")
        assert resp.status_code == 400
        assert "Too many IDs" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_1000_ids_rejected(self, client):
        ids = ",".join(str(i) for i in range(1, 1001))
        resp = await client.get(f"/api/v1/users/1/ratings/check?movie_ids={ids}")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_single_id_allowed(self, client):
        resp = await client.get("/api/v1/users/1/ratings/check?movie_ids=42")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_non_integer_ids_rejected(self, client):
        resp = await client.get("/api/v1/users/1/ratings/check?movie_ids=abc,def")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_mixed_valid_invalid_ids_rejected(self, client):
        resp = await client.get("/api/v1/users/1/ratings/check?movie_ids=1,abc,3")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_ids_after_parse(self, client):
        resp = await client.get("/api/v1/users/1/ratings/check?movie_ids=")
        # Either 200 with empty or 422 depending on implementation
        assert resp.status_code in (200, 422)

    @pytest.mark.asyncio
    async def test_ids_with_whitespace_accepted(self, client):
        resp = await client.get("/api/v1/users/1/ratings/check?movie_ids=1, 2, 3")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Search query max_length
# ---------------------------------------------------------------------------
class TestSearchQueryLimits:
    @pytest.mark.asyncio
    async def test_search_query_within_limit(self, client):
        resp = await client.get("/api/v1/movies/search?q=the+matrix")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_search_query_at_max_length(self, client):
        q = "a" * 200
        resp = await client.get(f"/api/v1/movies/search?q={q}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_search_query_exceeds_max_length(self, client):
        q = "a" * 201
        resp = await client.get(f"/api/v1/movies/search?q={q}")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_search_query_empty_rejected(self, client):
        resp = await client.get("/api/v1/movies/search?q=")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_search_query_missing_rejected(self, client):
        resp = await client.get("/api/v1/movies/search")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Pagination bounds
# ---------------------------------------------------------------------------
class TestPaginationBounds:
    @pytest.mark.asyncio
    async def test_ratings_limit_max_100(self, client):
        resp = await client.get("/api/v1/users/1/ratings?limit=101")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ratings_limit_min_1(self, client):
        resp = await client.get("/api/v1/users/1/ratings?limit=0")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ratings_offset_non_negative(self, client):
        resp = await client.get("/api/v1/users/1/ratings?offset=-1")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ratings_valid_pagination(self, client):
        resp = await client.get("/api/v1/users/1/ratings?offset=0&limit=50")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_search_limit_max_100(self, client):
        resp = await client.get("/api/v1/movies/search?q=test&limit=101")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_search_limit_min_1(self, client):
        resp = await client.get("/api/v1/movies/search?q=test&limit=0")
        assert resp.status_code == 422
