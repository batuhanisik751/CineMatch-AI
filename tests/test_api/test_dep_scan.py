"""Tests for the dependency vulnerability scanning endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from cinematch.api.deps import get_current_user
from cinematch.main import create_app


def _make_user(id: int = 1):
    u = MagicMock()
    u.id = id
    u.email = "test@example.com"
    u.username = "testuser"
    return u


def _make_scan_result(vuln_count: int = 0, bandit_count: int = 0) -> dict:
    return {
        "pip_audit": {
            "available": True,
            "vulnerabilities": [
                {
                    "name": "requests",
                    "version": "2.25.0",
                    "vuln_id": "CVE-2023-1234",
                    "fix_versions": ["2.31.0"],
                    "description": "SSRF vulnerability",
                }
            ]
            * vuln_count,
            "dependency_count": 42,
            "vulnerable_count": vuln_count,
            "error": None,
        },
        "bandit": {
            "available": True,
            "results": [
                {
                    "filename": "src/app.py",
                    "line_number": 10,
                    "issue_text": "Use of assert",
                    "issue_severity": "LOW",
                    "issue_confidence": "HIGH",
                    "test_id": "B101",
                }
            ]
            * bandit_count,
            "severity_counts": {"LOW": bandit_count, "MEDIUM": 0, "HIGH": 0},
            "error": None,
        },
        "safety": {
            "available": False,
            "vulnerabilities": [],
            "error": "safety not found on PATH",
        },
        "summary": {
            "total_dependencies": 42,
            "vulnerable_dependencies": vuln_count,
            "bandit_issues": bandit_count,
            "overall_status": "pass" if vuln_count == 0 and bandit_count == 0 else "warning",
        },
    }


@pytest.fixture()
def dep_scan_app():
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    return app


@pytest.fixture()
async def dep_scan_client(dep_scan_app):
    transport = ASGITransport(app=dep_scan_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_dep_scan_returns_expected_shape(dep_scan_client):
    with patch(
        "cinematch.api.v1.dep_scan.run_full_scan",
        return_value=_make_scan_result(),
    ):
        resp = await dep_scan_client.get("/api/v1/system/dep-scan")
    assert resp.status_code == 200
    data = resp.json()
    assert "pip_audit" in data
    assert "bandit" in data
    assert "safety" in data
    assert "summary" in data
    assert "scanned_at" in data


@pytest.mark.asyncio
async def test_dep_scan_with_vulnerabilities(dep_scan_client):
    with patch(
        "cinematch.api.v1.dep_scan.run_full_scan",
        return_value=_make_scan_result(vuln_count=2, bandit_count=1),
    ):
        resp = await dep_scan_client.get("/api/v1/system/dep-scan")
    data = resp.json()
    assert len(data["pip_audit"]["vulnerabilities"]) == 2
    assert len(data["bandit"]["results"]) == 1
    assert data["summary"]["vulnerable_dependencies"] == 2


@pytest.mark.asyncio
async def test_dep_scan_tools_unavailable(dep_scan_client):
    result = {
        "pip_audit": {
            "available": False,
            "vulnerabilities": [],
            "dependency_count": 0,
            "vulnerable_count": 0,
            "error": "pip-audit not found on PATH",
        },
        "bandit": {
            "available": False,
            "results": [],
            "severity_counts": {},
            "error": "bandit not found on PATH",
        },
        "safety": {
            "available": False,
            "vulnerabilities": [],
            "error": "safety not found on PATH",
        },
        "summary": {
            "total_dependencies": 0,
            "vulnerable_dependencies": 0,
            "bandit_issues": 0,
            "overall_status": "pass",
        },
    }
    with patch(
        "cinematch.api.v1.dep_scan.run_full_scan",
        return_value=result,
    ):
        resp = await dep_scan_client.get("/api/v1/system/dep-scan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pip_audit"]["available"] is False
    assert data["bandit"]["available"] is False


@pytest.mark.asyncio
async def test_dep_scan_requires_auth():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/system/dep-scan")
    assert resp.status_code == 401
