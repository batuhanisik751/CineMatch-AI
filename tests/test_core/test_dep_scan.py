"""Tests for the dependency vulnerability scanning core logic."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

from cinematch.core.dep_scan import (
    run_bandit_scan,
    run_full_scan,
    run_pip_audit,
    run_safety_check,
)

# ---------------------------------------------------------------------------
# pip-audit tests
# ---------------------------------------------------------------------------


def _pip_audit_json(deps: list[dict]) -> str:
    return json.dumps({"dependencies": deps})


def test_run_pip_audit_no_vulnerabilities():
    stdout = _pip_audit_json([{"name": "fastapi", "version": "0.110.0", "vulns": []}])
    proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")
    with (
        patch("cinematch.core.dep_scan.check_tool_available", return_value=True),
        patch("subprocess.run", return_value=proc),
    ):
        result = run_pip_audit()
    assert result["available"] is True
    assert result["vulnerabilities"] == []
    assert result["dependency_count"] == 1
    assert result["vulnerable_count"] == 0
    assert result["error"] is None


def test_run_pip_audit_with_vulnerabilities():
    stdout = _pip_audit_json(
        [
            {
                "name": "requests",
                "version": "2.25.0",
                "vulns": [
                    {
                        "id": "CVE-2023-1234",
                        "fix_versions": ["2.31.0"],
                        "description": "SSRF vulnerability",
                    }
                ],
            }
        ]
    )
    proc = subprocess.CompletedProcess(args=[], returncode=1, stdout=stdout, stderr="")
    with (
        patch("cinematch.core.dep_scan.check_tool_available", return_value=True),
        patch("subprocess.run", return_value=proc),
    ):
        result = run_pip_audit()
    assert result["available"] is True
    assert len(result["vulnerabilities"]) == 1
    assert result["vulnerabilities"][0]["vuln_id"] == "CVE-2023-1234"
    assert result["vulnerable_count"] == 1


def test_run_pip_audit_not_installed():
    with patch("cinematch.core.dep_scan.check_tool_available", return_value=False):
        result = run_pip_audit()
    assert result["available"] is False
    assert "not found" in result["error"]


def test_run_pip_audit_timeout():
    with (
        patch("cinematch.core.dep_scan.check_tool_available", return_value=True),
        patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pip-audit", timeout=5)),
    ):
        result = run_pip_audit(timeout=5)
    assert result["available"] is True
    assert "timed out" in result["error"]


# ---------------------------------------------------------------------------
# bandit tests
# ---------------------------------------------------------------------------


def _bandit_json(results: list[dict], totals: dict | None = None) -> str:
    if totals is None:
        totals = {"SEVERITY.LOW": 0, "SEVERITY.MEDIUM": 0, "SEVERITY.HIGH": 0}
    return json.dumps({"results": results, "metrics": {"_totals": totals}})


def test_run_bandit_clean():
    stdout = _bandit_json([])
    proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")
    with (
        patch("cinematch.core.dep_scan.check_tool_available", return_value=True),
        patch("subprocess.run", return_value=proc),
    ):
        result = run_bandit_scan()
    assert result["available"] is True
    assert result["results"] == []
    assert result["error"] is None


def test_run_bandit_with_findings():
    finding = {
        "filename": "src/app.py",
        "line_number": 42,
        "issue_text": "Use of assert detected.",
        "issue_severity": "LOW",
        "issue_confidence": "HIGH",
        "test_id": "B101",
    }
    stdout = _bandit_json(
        [finding],
        {"SEVERITY.LOW": 1, "SEVERITY.MEDIUM": 0, "SEVERITY.HIGH": 0},
    )
    proc = subprocess.CompletedProcess(args=[], returncode=1, stdout=stdout, stderr="")
    with (
        patch("cinematch.core.dep_scan.check_tool_available", return_value=True),
        patch("subprocess.run", return_value=proc),
    ):
        result = run_bandit_scan()
    assert len(result["results"]) == 1
    assert result["results"][0]["test_id"] == "B101"
    assert result["severity_counts"]["LOW"] == 1


def test_run_bandit_not_installed():
    with patch("cinematch.core.dep_scan.check_tool_available", return_value=False):
        result = run_bandit_scan()
    assert result["available"] is False
    assert "not found" in result["error"]


# ---------------------------------------------------------------------------
# safety tests
# ---------------------------------------------------------------------------


def test_run_safety_check_clean():
    proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
    with (
        patch("cinematch.core.dep_scan.check_tool_available", return_value=True),
        patch("subprocess.run", return_value=proc),
    ):
        result = run_safety_check()
    assert result["available"] is True
    assert result["vulnerabilities"] == []
    assert result["error"] is None


# ---------------------------------------------------------------------------
# Full scan / overall_status tests
# ---------------------------------------------------------------------------


def _make_pip_result(vuln_count: int = 0) -> dict:
    vuln = {
        "name": "pkg",
        "version": "1.0",
        "vuln_id": "CVE-X",
        "fix_versions": [],
        "description": "",
    }
    return {
        "available": True,
        "vulnerabilities": [vuln] * vuln_count,
        "dependency_count": 10,
        "vulnerable_count": vuln_count,
        "error": None,
    }


def _make_bandit_result(low: int = 0, medium: int = 0, high: int = 0) -> dict:
    finding = {
        "filename": "f.py",
        "line_number": 1,
        "issue_text": "x",
        "issue_severity": "LOW",
        "issue_confidence": "HIGH",
        "test_id": "B101",
    }
    results = [finding] * (low + medium + high)
    return {
        "available": True,
        "results": results,
        "severity_counts": {"LOW": low, "MEDIUM": medium, "HIGH": high},
        "error": None,
    }


def _make_safety_result(vuln_count: int = 0) -> dict:
    vuln = {
        "name": "pkg",
        "version": "1.0",
        "vuln_id": "CVE-X",
        "fix_versions": [],
        "description": "",
    }
    return {
        "available": True,
        "vulnerabilities": [vuln] * vuln_count,
        "error": None,
    }


def test_run_full_scan_overall_status_pass():
    _pip = "cinematch.core.dep_scan.run_pip_audit"
    _ban = "cinematch.core.dep_scan.run_bandit_scan"
    _saf = "cinematch.core.dep_scan.run_safety_check"
    with (
        patch(_pip, return_value=_make_pip_result(0)),
        patch(_ban, return_value=_make_bandit_result()),
        patch(_saf, return_value=_make_safety_result()),
    ):
        result = run_full_scan()
    assert result["summary"]["overall_status"] == "pass"


def test_run_full_scan_overall_status_warning():
    _pip = "cinematch.core.dep_scan.run_pip_audit"
    _ban = "cinematch.core.dep_scan.run_bandit_scan"
    _saf = "cinematch.core.dep_scan.run_safety_check"
    with (
        patch(_pip, return_value=_make_pip_result(0)),
        patch(_ban, return_value=_make_bandit_result(low=2)),
        patch(_saf, return_value=_make_safety_result()),
    ):
        result = run_full_scan()
    assert result["summary"]["overall_status"] == "warning"


def test_run_full_scan_overall_status_fail_vulns():
    _pip = "cinematch.core.dep_scan.run_pip_audit"
    _ban = "cinematch.core.dep_scan.run_bandit_scan"
    _saf = "cinematch.core.dep_scan.run_safety_check"
    with (
        patch(_pip, return_value=_make_pip_result(1)),
        patch(_ban, return_value=_make_bandit_result()),
        patch(_saf, return_value=_make_safety_result()),
    ):
        result = run_full_scan()
    assert result["summary"]["overall_status"] == "fail"


def test_run_full_scan_overall_status_fail_high_bandit():
    _pip = "cinematch.core.dep_scan.run_pip_audit"
    _ban = "cinematch.core.dep_scan.run_bandit_scan"
    _saf = "cinematch.core.dep_scan.run_safety_check"
    with (
        patch(_pip, return_value=_make_pip_result(0)),
        patch(_ban, return_value=_make_bandit_result(high=1)),
        patch(_saf, return_value=_make_safety_result()),
    ):
        result = run_full_scan()
    assert result["summary"]["overall_status"] == "fail"
