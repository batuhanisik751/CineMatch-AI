"""Custom exceptions and FastAPI exception handlers."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


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
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def service_unavailable_handler(
    request: Request, exc: ServiceUnavailableError
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})
