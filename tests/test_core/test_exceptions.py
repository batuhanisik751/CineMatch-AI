"""Tests for custom exception handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from cinematch.core.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    not_found_handler,
    service_unavailable_handler,
)


@pytest.mark.asyncio
async def test_not_found_handler_returns_404():
    request = AsyncMock()
    exc = NotFoundError("Movie", 42)
    response = await not_found_handler(request, exc)
    assert response.status_code == 404
    assert b"The requested resource was not found." in response.body


@pytest.mark.asyncio
async def test_service_unavailable_handler_returns_503():
    request = AsyncMock()
    exc = ServiceUnavailableError("LLM service")
    response = await service_unavailable_handler(request, exc)
    assert response.status_code == 503
    assert b"Service temporarily unavailable. Please try again later." in response.body


def test_not_found_error_message():
    exc = NotFoundError("User", 99)
    assert str(exc) == "User with id 99 not found"
    assert exc.resource == "User"
    assert exc.resource_id == 99


def test_service_unavailable_error_message():
    exc = ServiceUnavailableError("Redis")
    assert str(exc) == "Redis is not available"
    assert exc.service == "Redis"
