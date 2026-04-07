"""Custom exceptions and FastAPI exception handlers."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class CineMatchError(Exception):
    """Base exception for CineMatch-AI."""


class NotFoundError(CineMatchError):
    """Resource not found."""

    def __init__(self, resource: str, resource_id: int) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} with id {resource_id} not found")


class ServiceUnavailableError(CineMatchError):
    """Service is not available (e.g., LLM disabled)."""

    def __init__(self, service: str) -> None:
        self.service = service
        super().__init__(f"{service} is not available")


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    logger.warning(
        "NotFoundError: %s id=%s, path=%s",
        exc.resource,
        exc.resource_id,
        request.url.path,
    )
    return JSONResponse(
        status_code=404,
        content={"detail": "The requested resource was not found."},
    )


async def service_unavailable_handler(
    request: Request, exc: ServiceUnavailableError
) -> JSONResponse:
    logger.error(
        "ServiceUnavailableError: %s, path=%s",
        exc.service,
        request.url.path,
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "Service temporarily unavailable. Please try again later."},
    )


async def catch_all_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred.", "debug_error": str(exc)},
    )
