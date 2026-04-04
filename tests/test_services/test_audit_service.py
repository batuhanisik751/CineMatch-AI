"""Tests for AuditService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cinematch.services.audit_service import AuditService


@pytest.fixture()
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture()
def service():
    return AuditService(log_file=None, enabled=True)


@pytest.fixture()
def disabled_service():
    return AuditService(log_file=None, enabled=False)


@pytest.mark.asyncio
async def test_log_creates_db_entry(service, mock_db):
    """log() inserts an AuditLog row into the database."""
    await service.log(
        "auth.login",
        mock_db,
        user_id=1,
        ip_address="127.0.0.1",
        user_agent="TestAgent",
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()

    entry = mock_db.add.call_args[0][0]
    assert entry.action == "auth.login"
    assert entry.user_id == 1
    assert entry.ip_address == "127.0.0.1"
    assert entry.user_agent == "TestAgent"
    assert entry.status == "success"


@pytest.mark.asyncio
async def test_log_with_detail(service, mock_db):
    """log() stores detail as JSON string."""
    await service.log(
        "data.import",
        mock_db,
        user_id=1,
        detail={"source": "letterboxd", "rows": 150},
    )
    entry = mock_db.add.call_args[0][0]
    assert '"source": "letterboxd"' in entry.detail
    assert '"rows": 150' in entry.detail


@pytest.mark.asyncio
async def test_log_failure_status(service, mock_db):
    """log() records failure status."""
    await service.log(
        "auth.login_failed",
        mock_db,
        detail={"email": "bad@test.com"},
        status="failure",
    )
    entry = mock_db.add.call_args[0][0]
    assert entry.status == "failure"
    assert entry.action == "auth.login_failed"


@pytest.mark.asyncio
async def test_log_disabled_skips_write(disabled_service, mock_db):
    """When enabled=False, log() does nothing."""
    await disabled_service.log("auth.login", mock_db, user_id=1)
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_log_writes_to_file(mock_db, tmp_path):
    """log() writes a JSON line to the audit file."""
    log_file = str(tmp_path / "audit.log")
    svc = AuditService(log_file=log_file, enabled=True)

    await svc.log("auth.login", mock_db, user_id=42, ip_address="10.0.0.1")

    with open(log_file) as f:
        content = f.read()
    assert "auth.login" in content
    assert "10.0.0.1" in content


@pytest.mark.asyncio
async def test_query_returns_filtered_results(mock_db):
    """query() applies filters and returns (rows, total)."""
    service = AuditService(enabled=True)

    mock_result_count = MagicMock()
    mock_result_count.scalar_one.return_value = 3

    mock_result_rows = MagicMock()
    mock_result_rows.scalars.return_value.all.return_value = ["row1", "row2", "row3"]

    mock_db.execute = AsyncMock(side_effect=[mock_result_count, mock_result_rows])

    rows, total = await service.query(mock_db, user_id=1, action="auth.login")

    assert total == 3
    assert len(rows) == 3
    assert mock_db.execute.await_count == 2


@pytest.mark.asyncio
async def test_query_pagination(mock_db):
    """query() respects offset and limit."""
    service = AuditService(enabled=True)

    mock_result_count = MagicMock()
    mock_result_count.scalar_one.return_value = 100

    mock_result_rows = MagicMock()
    mock_result_rows.scalars.return_value.all.return_value = ["row1", "row2"]

    mock_db.execute = AsyncMock(side_effect=[mock_result_count, mock_result_rows])

    rows, total = await service.query(mock_db, user_id=1, offset=10, limit=2)

    assert total == 100
    assert len(rows) == 2
