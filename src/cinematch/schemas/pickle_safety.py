"""Pickle artifact integrity status schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PickleArtifactStatus(BaseModel):
    file_name: str
    file_path: str
    expected_hash: str | None
    actual_hash: str | None
    status: str
    file_size_bytes: int | None
    last_modified: datetime | None


class PickleSafetyResponse(BaseModel):
    artifacts: list[PickleArtifactStatus]
    all_verified: bool
    checked_at: datetime
