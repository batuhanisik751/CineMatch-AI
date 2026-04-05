"""Extensive tests for error response hardening (Phase 8).

Verifies:
- Generic error messages returned (no internal details leaked)
- Catch-all handler for unhandled exceptions
- No stack traces, file paths, or service names in responses
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.core.exceptions import (
    CineMatchError,
    NotFoundError,
    ServiceUnavailableError,
    catch_all_handler,
    not_found_handler,
    service_unavailable_handler,
)


# ---------------------------------------------------------------------------
# NotFoundError handler
# ---------------------------------------------------------------------------
class TestNotFoundHandler:
    @pytest.mark.asyncio
    async def test_returns_404(self):
        request = AsyncMock()
        exc = NotFoundError("Movie", 42)
        response = await not_found_handler(request, exc)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generic_message_no_resource_details(self):
        request = AsyncMock()
        exc = NotFoundError("Movie", 99999)
        response = await not_found_handler(request, exc)
        body = json.loads(response.body)
        assert body["detail"] == "The requested resource was not found."
        # Must NOT contain the actual resource type or ID
        assert "Movie" not in body["detail"]
        assert "99999" not in body["detail"]

    @pytest.mark.asyncio
    async def test_no_stack_trace_in_response(self):
        request = AsyncMock()
        exc = NotFoundError("User", 1)
        response = await not_found_handler(request, exc)
        body_text = response.body.decode()
        assert "Traceback" not in body_text
        assert ".py" not in body_text

    @pytest.mark.asyncio
    async def test_different_resources_same_message(self):
        """All NotFoundErrors produce the same generic message."""
        request = AsyncMock()
        for resource, rid in [("Movie", 1), ("User", 999), ("Rating", 0)]:
            exc = NotFoundError(resource, rid)
            response = await not_found_handler(request, exc)
            body = json.loads(response.body)
            assert body["detail"] == "The requested resource was not found."


# ---------------------------------------------------------------------------
# ServiceUnavailableError handler
# ---------------------------------------------------------------------------
class TestServiceUnavailableHandler:
    @pytest.mark.asyncio
    async def test_returns_503(self):
        request = AsyncMock()
        exc = ServiceUnavailableError("LLM service")
        response = await service_unavailable_handler(request, exc)
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_generic_message_no_service_name(self):
        request = AsyncMock()
        exc = ServiceUnavailableError("LLM service")
        response = await service_unavailable_handler(request, exc)
        body = json.loads(response.body)
        assert body["detail"] == "Service temporarily unavailable. Please try again later."
        # Must NOT reveal which service is down
        assert "LLM" not in body["detail"]

    @pytest.mark.asyncio
    async def test_different_services_same_message(self):
        request = AsyncMock()
        for service in ["LLM service", "Redis", "Embedding model", "FAISS index"]:
            exc = ServiceUnavailableError(service)
            response = await service_unavailable_handler(request, exc)
            body = json.loads(response.body)
            assert body["detail"] == "Service temporarily unavailable. Please try again later."

    @pytest.mark.asyncio
    async def test_no_service_topology_leaked(self):
        request = AsyncMock()
        exc = ServiceUnavailableError("Redis cache on port 6379")
        response = await service_unavailable_handler(request, exc)
        body_text = response.body.decode()
        assert "Redis" not in body_text
        assert "6379" not in body_text


# ---------------------------------------------------------------------------
# Catch-all handler
# ---------------------------------------------------------------------------
class TestCatchAllHandler:
    @pytest.mark.asyncio
    async def test_returns_500(self):
        request = AsyncMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/api/v1/movies"
        exc = RuntimeError("Unexpected database corruption")
        response = await catch_all_handler(request, exc)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_generic_message(self):
        request = AsyncMock()
        request.method = "POST"
        request.url = MagicMock()
        request.url.path = "/api/v1/users/1/ratings"
        exc = ValueError("column 'rating' out of range")
        response = await catch_all_handler(request, exc)
        body = json.loads(response.body)
        assert body["detail"] == "An unexpected error occurred."

    @pytest.mark.asyncio
    async def test_no_exception_details_in_response(self):
        request = AsyncMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"
        exc = Exception("sensitive: password=hunter2, db=prod-main")
        response = await catch_all_handler(request, exc)
        body_text = response.body.decode()
        assert "password" not in body_text
        assert "hunter2" not in body_text
        assert "prod-main" not in body_text
        assert "sensitive" not in body_text

    @pytest.mark.asyncio
    async def test_no_stack_trace_in_response(self):
        request = AsyncMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"
        exc = TypeError("'NoneType' object has no attribute 'id'")
        response = await catch_all_handler(request, exc)
        body_text = response.body.decode()
        assert "NoneType" not in body_text
        assert "Traceback" not in body_text

    @pytest.mark.asyncio
    async def test_no_file_paths_in_response(self):
        request = AsyncMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"
        exc = FileNotFoundError("/app/src/cinematch/services/movie_service.py")
        response = await catch_all_handler(request, exc)
        body_text = response.body.decode()
        assert "/app" not in body_text
        assert "movie_service" not in body_text

    @pytest.mark.asyncio
    async def test_handles_exception_subclasses(self):
        request = AsyncMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"
        exc = KeyError("user_id")
        response = await catch_all_handler(request, exc)
        assert response.status_code == 500
        body = json.loads(response.body)
        assert body["detail"] == "An unexpected error occurred."


# ---------------------------------------------------------------------------
# Error class internals (exception stores info, handler hides it)
# ---------------------------------------------------------------------------
class TestErrorClassesPreserveInfo:
    """Exceptions store details for logging, but handlers hide them from responses."""

    def test_not_found_stores_resource_and_id(self):
        exc = NotFoundError("Movie", 42)
        assert exc.resource == "Movie"
        assert exc.resource_id == 42
        assert "Movie with id 42" in str(exc)

    def test_service_unavailable_stores_service_name(self):
        exc = ServiceUnavailableError("Redis")
        assert exc.service == "Redis"
        assert "Redis" in str(exc)

    def test_cinematch_error_is_base(self):
        assert issubclass(NotFoundError, CineMatchError)
        assert issubclass(ServiceUnavailableError, CineMatchError)
        assert issubclass(CineMatchError, Exception)
