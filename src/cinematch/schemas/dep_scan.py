"""Dependency vulnerability scanning response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PipAuditVulnerability(BaseModel):
    name: str
    version: str
    vuln_id: str
    fix_versions: list[str]
    description: str


class PipAuditResult(BaseModel):
    available: bool
    vulnerabilities: list[PipAuditVulnerability]
    dependency_count: int
    vulnerable_count: int
    error: str | None


class BanditFinding(BaseModel):
    filename: str
    line_number: int
    issue_text: str
    issue_severity: str
    issue_confidence: str
    test_id: str


class BanditResult(BaseModel):
    available: bool
    results: list[BanditFinding]
    severity_counts: dict[str, int]
    error: str | None


class SafetyResult(BaseModel):
    available: bool
    vulnerabilities: list[PipAuditVulnerability]
    error: str | None


class DepScanSummary(BaseModel):
    total_dependencies: int
    vulnerable_dependencies: int
    bandit_issues: int
    overall_status: str


class DepScanResponse(BaseModel):
    pip_audit: PipAuditResult
    bandit: BanditResult
    safety: SafetyResult
    summary: DepScanSummary
    scanned_at: datetime
