"""Tests for audit log API endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest


def _make_audit_log(
    id: int = 1,
    action: str = "auth.login",
    user_id: int = 1,
    status: str = "success",
) -> MagicMock:
    log = MagicMock()
    log.id = id
    log.timestamp = datetime(2026, 4, 4, 12, 0, 0, tzinfo=UTC)
    log.user_id = user_id
    log.action = action
    log.detail = '{"key": "value"}'
    log.ip_address = "127.0.0.1"
    log.user_agent = "TestBrowser/1.0"
    log.status = status
    return log


@pytest.mark.asyncio
async def test_get_audit_logs_returns_user_logs(client, mock_audit_service):
    mock_audit_service.query.return_value = (
        [_make_audit_log(), _make_audit_log(id=2, action="data.import")],
        2,
    )
    resp = await client.get("/api/v1/users/audit-logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["logs"]) == 2
    assert data["logs"][0]["action"] == "auth.login"
    assert data["logs"][1]["action"] == "data.import"
    assert data["offset"] == 0
    assert data["limit"] == 50


@pytest.mark.asyncio
async def test_get_audit_logs_with_action_filter(client, mock_audit_service):
    mock_audit_service.query.return_value = ([_make_audit_log()], 1)
    resp = await client.get("/api/v1/users/audit-logs?action=auth.login")
    assert resp.status_code == 200
    # Verify the service was called with the action filter
    mock_audit_service.query.assert_awaited_once()
    call_kwargs = mock_audit_service.query.call_args
    assert call_kwargs.kwargs["action"] == "auth.login"


@pytest.mark.asyncio
async def test_get_audit_logs_with_status_filter(client, mock_audit_service):
    mock_audit_service.query.return_value = (
        [_make_audit_log(status="failure")],
        1,
    )
    resp = await client.get("/api/v1/users/audit-logs?status=failure")
    assert resp.status_code == 200
    data = resp.json()
    assert data["logs"][0]["status"] == "failure"


@pytest.mark.asyncio
async def test_get_audit_logs_pagination(client, mock_audit_service):
    mock_audit_service.query.return_value = ([], 0)
    resp = await client.get("/api/v1/users/audit-logs?offset=10&limit=5")
    assert resp.status_code == 200
    call_kwargs = mock_audit_service.query.call_args
    assert call_kwargs.kwargs["offset"] == 10
    assert call_kwargs.kwargs["limit"] == 5


@pytest.mark.asyncio
async def test_get_audit_logs_empty(client, mock_audit_service):
    mock_audit_service.query.return_value = ([], 0)
    resp = await client.get("/api/v1/users/audit-logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["logs"] == []


@pytest.mark.asyncio
async def test_get_audit_logs_detail_parsed(client, mock_audit_service):
    """Detail field should be parsed from JSON string to dict."""
    mock_audit_service.query.return_value = ([_make_audit_log()], 1)
    resp = await client.get("/api/v1/users/audit-logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["logs"][0]["detail"] == {"key": "value"}
