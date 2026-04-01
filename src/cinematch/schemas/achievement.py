"""Pydantic schemas for achievement badges."""

from __future__ import annotations

from pydantic import BaseModel


class AchievementBadge(BaseModel):
    """Single achievement badge with progress tracking."""

    id: str
    name: str
    description: str
    icon: str
    unlocked: bool
    progress: int
    target: int
    unlocked_detail: str | None = None


class AchievementResponse(BaseModel):
    """Full achievement response for a user."""

    user_id: int
    badges: list[AchievementBadge]
    unlocked_count: int
    total_count: int
