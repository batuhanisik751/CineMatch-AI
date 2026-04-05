"""Dependency vulnerability scanning via pip-audit, bandit, and safety."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def check_tool_available(name: str) -> bool:
    """Return True if *name* is found on PATH."""
    return shutil.which(name) is not None


def run_pip_audit(timeout: int = 120) -> dict:
    """Run pip-audit and return structured results."""
    if not check_tool_available("pip-audit"):
        return {
            "available": False,
            "vulnerabilities": [],
            "dependency_count": 0,
            "vulnerable_count": 0,
            "error": "pip-audit not found on PATH",
        }

    try:
        proc = subprocess.run(
            ["pip-audit", "--format=json", "--output=-"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        # pip-audit exits 1 when vulnerabilities are found — not an error
        data = json.loads(proc.stdout)

        vulns: list[dict] = []
        dep_count = 0
        if isinstance(data, dict):
            # Newer pip-audit JSON format
            deps = data.get("dependencies", [])
            dep_count = len(deps)
            for dep in deps:
                for v in dep.get("vulns", []):
                    vulns.append(
                        {
                            "name": dep.get("name", ""),
                            "version": dep.get("version", ""),
                            "vuln_id": v.get("id", ""),
                            "fix_versions": v.get("fix_versions", []),
                            "description": v.get("description", ""),
                        }
                    )
        elif isinstance(data, list):
            # Older pip-audit JSON format (flat list)
            dep_count = len(data)
            for entry in data:
                for v in entry.get("vulns", []):
                    vulns.append(
                        {
                            "name": entry.get("name", ""),
                            "version": entry.get("version", ""),
                            "vuln_id": v.get("id", ""),
                            "fix_versions": v.get("fix_versions", []),
                            "description": v.get("description", ""),
                        }
                    )

        return {
            "available": True,
            "vulnerabilities": vulns,
            "dependency_count": dep_count,
            "vulnerable_count": len(vulns),
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "vulnerabilities": [],
            "dependency_count": 0,
            "vulnerable_count": 0,
            "error": f"pip-audit timed out after {timeout}s",
        }
    except (json.JSONDecodeError, KeyError) as exc:
        return {
            "available": True,
            "vulnerabilities": [],
            "dependency_count": 0,
            "vulnerable_count": 0,
            "error": f"Failed to parse pip-audit output: {exc}",
        }


def run_bandit_scan(target: str = "src/", timeout: int = 120) -> dict:
    """Run bandit static analysis and return structured results."""
    if not check_tool_available("bandit"):
        return {
            "available": False,
            "results": [],
            "severity_counts": {},
            "error": "bandit not found on PATH",
        }

    try:
        proc = subprocess.run(
            ["bandit", "-r", target, "-f", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        # bandit exits 1 when issues are found — not an error
        data = json.loads(proc.stdout)

        results = [
            {
                "filename": r.get("filename", ""),
                "line_number": r.get("line_number", 0),
                "issue_text": r.get("issue_text", ""),
                "issue_severity": r.get("issue_severity", ""),
                "issue_confidence": r.get("issue_confidence", ""),
                "test_id": r.get("test_id", ""),
            }
            for r in data.get("results", [])
        ]

        metrics = data.get("metrics", {}).get("_totals", {})
        severity_counts = {
            "LOW": metrics.get("SEVERITY.LOW", 0),
            "MEDIUM": metrics.get("SEVERITY.MEDIUM", 0),
            "HIGH": metrics.get("SEVERITY.HIGH", 0),
        }

        return {
            "available": True,
            "results": results,
            "severity_counts": severity_counts,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "results": [],
            "severity_counts": {},
            "error": f"bandit timed out after {timeout}s",
        }
    except (json.JSONDecodeError, KeyError) as exc:
        return {
            "available": True,
            "results": [],
            "severity_counts": {},
            "error": f"Failed to parse bandit output: {exc}",
        }


def run_safety_check(timeout: int = 120) -> dict:
    """Run safety check and return structured results."""
    if not check_tool_available("safety"):
        return {
            "available": False,
            "vulnerabilities": [],
            "error": "safety not found on PATH",
        }

    try:
        proc = subprocess.run(
            ["safety", "check", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        data = json.loads(proc.stdout)

        vulns: list[dict] = []
        # safety v3 JSON format: list of vulnerability dicts
        if isinstance(data, list):
            for entry in data:
                vulns.append(
                    {
                        "name": entry.get("package_name", entry.get("name", "")),
                        "version": entry.get("analyzed_version", entry.get("version", "")),
                        "vuln_id": entry.get("vulnerability_id", entry.get("id", "")),
                        "fix_versions": [],
                        "description": entry.get("advisory", entry.get("description", "")),
                    }
                )
        elif isinstance(data, dict):
            for entry in data.get("vulnerabilities", data.get("results", [])):
                vulns.append(
                    {
                        "name": entry.get("package_name", entry.get("name", "")),
                        "version": entry.get("analyzed_version", entry.get("version", "")),
                        "vuln_id": entry.get("vulnerability_id", entry.get("id", "")),
                        "fix_versions": [],
                        "description": entry.get("advisory", entry.get("description", "")),
                    }
                )

        return {
            "available": True,
            "vulnerabilities": vulns,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "vulnerabilities": [],
            "error": f"safety timed out after {timeout}s",
        }
    except (json.JSONDecodeError, KeyError) as exc:
        return {
            "available": True,
            "vulnerabilities": [],
            "error": f"Failed to parse safety output: {exc}",
        }


def run_full_scan(timeout: int = 120) -> dict:
    """Run all scanning tools and return aggregated results."""
    pip_result = run_pip_audit(timeout=timeout)
    bandit_result = run_bandit_scan(timeout=timeout)
    safety_result = run_safety_check(timeout=timeout)

    vuln_count = pip_result["vulnerable_count"] + len(safety_result["vulnerabilities"])
    bandit_issue_count = len(bandit_result["results"])
    bandit_high = bandit_result.get("severity_counts", {}).get("HIGH", 0)

    if vuln_count > 0 or bandit_high > 0:
        overall_status = "fail"
    elif bandit_issue_count > 0:
        overall_status = "warning"
    else:
        overall_status = "pass"

    return {
        "pip_audit": pip_result,
        "bandit": bandit_result,
        "safety": safety_result,
        "summary": {
            "total_dependencies": pip_result["dependency_count"],
            "vulnerable_dependencies": vuln_count,
            "bandit_issues": bandit_issue_count,
            "overall_status": overall_status,
        },
    }
