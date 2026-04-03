"""Dismissal API endpoints (nested under /users)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import (
    get_cache_service,
    get_current_user,
    get_db,
    get_dismissal_service,
    get_movie_service,
    require_same_user,
)
from cinematch.core.cache import CacheService
from cinematch.models.user import User
from cinematch.schemas.dismissal import (
    DismissalBulkStatusResponse,
    DismissalCreate,
    DismissalItemResponse,
    DismissalListResponse,
    DismissalResponse,
)
from cinematch.services.dismissal_service import DismissalService
from cinematch.services.movie_service import MovieService

router = APIRouter()


@router.get(
    "/users/{user_id}/dismissals/check",
    response_model=DismissalBulkStatusResponse,
)
async def bulk_check_dismissals(
    user_id: int,
    movie_ids: str = Query(..., description="Comma-separated movie IDs"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    dismissal_service: DismissalService = Depends(get_dismissal_service),
):
    """Check which movies from a list are dismissed by the user."""
    require_same_user(current_user.id, user_id)
    try:
        id_list = [int(x.strip()) for x in movie_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="movie_ids must be comma-separated integers")

    dismissed = await dismissal_service.bulk_check(user_id, id_list, db)
    return DismissalBulkStatusResponse(movie_ids=sorted(dismissed))


@router.post(
    "/users/{user_id}/dismissals",
    response_model=DismissalResponse,
    status_code=201,
)
async def dismiss_movie(
    user_id: int,
    body: DismissalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    dismissal_service: DismissalService = Depends(get_dismissal_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Mark a movie as 'not interested'."""
    require_same_user(current_user.id, user_id)
    movie = await movie_service.get_by_id(body.movie_id, db)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    dismissal = await dismissal_service.dismiss_movie(user_id, body.movie_id, db)

    # Invalidate cached recommendations for this user
    if cache is not None:
        try:
            await cache.invalidate_user_recs(user_id)
        except Exception:
            pass

    resp = DismissalResponse.model_validate(dismissal)
    resp.movie_title = movie.title
    return resp


@router.delete(
    "/users/{user_id}/dismissals/{movie_id}",
    status_code=204,
)
async def undismiss_movie(
    user_id: int,
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    dismissal_service: DismissalService = Depends(get_dismissal_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Remove a dismissal (undo 'not interested')."""
    require_same_user(current_user.id, user_id)
    removed = await dismissal_service.undismiss_movie(user_id, movie_id, db)
    if not removed:
        raise HTTPException(status_code=404, detail="Movie not dismissed")

    # Invalidate cached recommendations for this user
    if cache is not None:
        try:
            await cache.invalidate_user_recs(user_id)
        except Exception:
            pass


@router.get(
    "/users/{user_id}/dismissals",
    response_model=DismissalListResponse,
)
async def get_dismissals(
    user_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    dismissal_service: DismissalService = Depends(get_dismissal_service),
):
    """Get the user's dismissed movies with details."""
    require_same_user(current_user.id, user_id)
    rows, total = await dismissal_service.get_dismissals(user_id, db, offset=offset, limit=limit)
    items = []
    for item, title, poster_path, genres, vote_average, release_date in rows:
        resp = DismissalItemResponse.model_validate(item)
        resp.movie_title = title
        resp.poster_path = poster_path
        resp.genres = genres or []
        resp.vote_average = vote_average or 0.0
        resp.release_date = str(release_date) if release_date else None
        items.append(resp)
    return DismissalListResponse(
        user_id=user_id,
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )
