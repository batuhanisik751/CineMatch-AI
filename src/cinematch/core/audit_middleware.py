"""Middleware that logs authorization failures and rate-limit hits to the audit service."""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from cinematch.db.session import async_session

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Intercept 403 and 429 responses to create audit log entries."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if response.status_code not in (403, 429):
            return response

        audit_service = getattr(request.app.state, "audit_service", None)
        if audit_service is None:
            return response

        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        detail = {"path": request.url.path, "method": request.method}

        if response.status_code == 403:
            action = "auth.forbidden"
            status = "failure"
        else:
            action = "rate_limit.exceeded"
            status = "failure"

        try:
            async with async_session() as db:
                await audit_service.log(
                    action,
                    db,
                    ip_address=ip,
                    user_agent=ua,
                    detail=detail,
                    status=status,
                )
        except Exception:
            logger.warning("Failed to write audit log for %s response", response.status_code)

        return response
