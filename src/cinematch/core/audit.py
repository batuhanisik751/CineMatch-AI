"""Audit logging utilities — JSON formatter and file handler."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime


class AuditJsonFormatter(logging.Formatter):
    """Format log records as single-line JSON for the audit log file."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "message": record.getMessage(),
        }
        # Merge any extra fields attached to the record
        if hasattr(record, "audit_data"):
            log_entry.update(record.audit_data)
        return json.dumps(log_entry, default=str)


def get_audit_file_handler(path: str) -> logging.FileHandler:
    """Create a file handler with JSON formatting for audit logs."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(AuditJsonFormatter())
    handler.setLevel(logging.INFO)
    return handler
