"""User API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_db, get_user_stats_service
from cinematch.models.user import User
from cinematch.schemas.user import UserResponse, UserStatsResponse
from cinematch.services.user_stats_service import UserStatsService

router = APIRouter()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    stats_service: UserStatsService = Depends(get_user_stats_service),
):
    stats = await stats_service.get_user_stats(user_id, db)
    return UserStatsResponse(**stats)
