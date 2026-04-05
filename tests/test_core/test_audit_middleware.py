"""Extensive tests for AuditMiddleware — intercepts 403 and 429 responses."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

from cinematch.core.audit_middleware import AuditMiddleware


def _make_request(
    path: str = "/api/v1/test",
    method: str = "GET",
    client_host: str = "127.0.0.1",
    user_agent: str = "TestAgent/1.0",
) -> MagicMock:
    request = MagicMock(spec=Request)
    request.url = MagicMock()
    request.url.path = path
    request.method = method
    request.client = MagicMock()
    request.client.host = client_host
    request.headers = {"user-agent": user_agent}
    request.app = MagicMock()
    return request


class TestAuditMiddleware:
    """Tests for AuditMiddleware dispatch logic."""

    @pytest.mark.asyncio
    async def test_passes_through_200_without_logging(self):
        middleware = AuditMiddleware(app=MagicMock())
        request = _make_request()
        mock_audit = AsyncMock()
        mock_audit.log.return_value = None
        request.app.state.audit_service = mock_audit

        response = Response(status_code=200)

        async def call_next(_):
            return response

        result = await middleware.dispatch(request, call_next)
        assert result.status_code == 200
        mock_audit.log.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_passes_through_201_without_logging(self):
        middleware = AuditMiddleware(app=MagicMock())
        request = _make_request()
        mock_audit = AsyncMock()
        request.app.state.audit_service = mock_audit

        response = Response(status_code=201)

        async def call_next(_):
            return response

        result = await middleware.dispatch(request, call_next)
        assert result.status_code == 201
        mock_audit.log.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_passes_through_404_without_logging(self):
        middleware = AuditMiddleware(app=MagicMock())
        request = _make_request()
        mock_audit = AsyncMock()
        request.app.state.audit_service = mock_audit

        response = Response(status_code=404)

        async def call_next(_):
            return response

        result = await middleware.dispatch(request, call_next)
        assert result.status_code == 404
        mock_audit.log.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_passes_through_500_without_logging(self):
        middleware = AuditMiddleware(app=MagicMock())
        request = _make_request()
        mock_audit = AsyncMock()
        request.app.state.audit_service = mock_audit

        response = Response(status_code=500)

        async def call_next(_):
            return response

        result = await middleware.dispatch(request, call_next)
        assert result.status_code == 500
        mock_audit.log.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_logs_403_as_auth_forbidden(self):
        middleware = AuditMiddleware(app=MagicMock())
        request = _make_request(path="/api/v1/users/2/ratings", client_host="10.0.0.5")
        mock_audit = AsyncMock()
        mock_audit.log.return_value = None
        request.app.state.audit_service = mock_audit

        response = Response(status_code=403)

        async def call_next(_):
            return response

        with patch("cinematch.core.audit_middleware.async_session") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await middleware.dispatch(request, call_next)

        assert result.status_code == 403
        mock_audit.log.assert_awaited_once()
        call_args = mock_audit.log.call_args
        assert call_args[0][0] == "auth.forbidden"
        assert call_args.kwargs["status"] == "failure"
        assert call_args.kwargs["ip_address"] == "10.0.0.5"

    @pytest.mark.asyncio
    async def test_logs_429_as_rate_limit_exceeded(self):
        middleware = AuditMiddleware(app=MagicMock())
        request = _make_request(path="/api/v1/auth/login", user_agent="BruteForcer/1.0")
        mock_audit = AsyncMock()
        mock_audit.log.return_value = None
        request.app.state.audit_service = mock_audit

        response = Response(status_code=429)

        async def call_next(_):
            return response

        with patch("cinematch.core.audit_middleware.async_session") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await middleware.dispatch(request, call_next)

        assert result.status_code == 429
        mock_audit.log.assert_awaited_once()
        call_args = mock_audit.log.call_args
        assert call_args[0][0] == "rate_limit.exceeded"
        assert call_args.kwargs["status"] == "failure"
        assert call_args.kwargs["user_agent"] == "BruteForcer/1.0"

    @pytest.mark.asyncio
    async def test_403_log_includes_path_and_method(self):
        middleware = AuditMiddleware(app=MagicMock())
        request = _make_request(path="/api/v1/users/99/ratings", method="POST")
        mock_audit = AsyncMock()
        mock_audit.log.return_value = None
        request.app.state.audit_service = mock_audit

        response = Response(status_code=403)

        async def call_next(_):
            return response

        with patch("cinematch.core.audit_middleware.async_session") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await middleware.dispatch(request, call_next)

        detail = mock_audit.log.call_args.kwargs["detail"]
        assert detail["path"] == "/api/v1/users/99/ratings"
        assert detail["method"] == "POST"

    @pytest.mark.asyncio
    async def test_no_audit_service_doesnt_crash(self):
        middleware = AuditMiddleware(app=MagicMock())
        request = _make_request()
        request.app.state = MagicMock(spec=[])  # No audit_service attribute

        response = Response(status_code=403)

        async def call_next(_):
            return response

        result = await middleware.dispatch(request, call_next)
        assert result.status_code == 403  # Still returns response

    @pytest.mark.asyncio
    async def test_audit_log_failure_doesnt_crash(self):
        middleware = AuditMiddleware(app=MagicMock())
        request = _make_request()
        mock_audit = AsyncMock()
        mock_audit.log.side_effect = Exception("DB connection failed")
        request.app.state.audit_service = mock_audit

        response = Response(status_code=403)

        async def call_next(_):
            return response

        with patch("cinematch.core.audit_middleware.async_session") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await middleware.dispatch(request, call_next)

        # Should not crash — graceful degradation
        assert result.status_code == 403

    @pytest.mark.asyncio
    async def test_no_client_info_handled(self):
        middleware = AuditMiddleware(app=MagicMock())
        request = _make_request()
        request.client = None  # No client info
        request.headers = {}  # No user-agent
        mock_audit = AsyncMock()
        mock_audit.log.return_value = None
        request.app.state.audit_service = mock_audit

        response = Response(status_code=429)

        async def call_next(_):
            return response

        with patch("cinematch.core.audit_middleware.async_session") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await middleware.dispatch(request, call_next)

        assert result.status_code == 429
        call_args = mock_audit.log.call_args
        assert call_args.kwargs["ip_address"] is None
