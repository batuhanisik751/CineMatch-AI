"""Pydantic schemas for user endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """User details."""

    id: int
    movielens_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
