"""Watchlist API endpoints (nested under /users)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_db, get_movie_service, get_watchlist_service
from cinematch.schemas.watchlist import (
    WatchlistAdd,
    WatchlistBulkStatusResponse,
    WatchlistItemResponse,
    WatchlistResponse,
)
from cinematch.services.movie_service import MovieService
from cinematch.services.watchlist_service import WatchlistService

router = APIRouter()


@router.get(
    "/users/{user_id}/watchlist/check",
    response_model=WatchlistBulkStatusResponse,
)
async def bulk_check_watchlist(
    user_id: int,
    movie_ids: str = Query(..., description="Comma-separated movie IDs"),
    db: AsyncSession = Depends(get_db),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """Check which movies from a list are in the user's watchlist."""
    try:
        id_list = [int(x.strip()) for x in movie_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="movie_ids must be comma-separated integers")

    in_watchlist = await watchlist_service.bulk_check(user_id, id_list, db)
    return WatchlistBulkStatusResponse(movie_ids=sorted(in_watchlist))


@router.post(
    "/users/{user_id}/watchlist",
    response_model=WatchlistItemResponse,
    status_code=201,
)
async def add_to_watchlist(
    user_id: int,
    body: WatchlistAdd,
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """Add a movie to the user's watchlist."""
    movie = await movie_service.get_by_id(body.movie_id, db)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    item = await watchlist_service.add_to_watchlist(user_id, body.movie_id, db)

    resp = WatchlistItemResponse.model_validate(item)
    resp.movie_title = movie.title
    resp.poster_path = movie.poster_path
    resp.genres = movie.genres or []
    resp.vote_average = movie.vote_average
    resp.release_date = str(movie.release_date) if movie.release_date else None
    return resp


@router.delete(
    "/users/{user_id}/watchlist/{movie_id}",
    status_code=204,
)
async def remove_from_watchlist(
    user_id: int,
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """Remove a movie from the user's watchlist."""
    removed = await watchlist_service.remove_from_watchlist(user_id, movie_id, db)
    if not removed:
        raise HTTPException(status_code=404, detail="Movie not in watchlist")


@router.get(
    "/users/{user_id}/watchlist",
    response_model=WatchlistResponse,
)
async def get_watchlist(
    user_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """Get a user's watchlist with movie details."""
    rows, total = await watchlist_service.get_watchlist(user_id, db, offset=offset, limit=limit)
    items = []
    for item, title, poster_path, genres, vote_average, release_date in rows:
        resp = WatchlistItemResponse.model_validate(item)
        resp.movie_title = title
        resp.poster_path = poster_path
        resp.genres = genres or []
        resp.vote_average = vote_average or 0.0
        resp.release_date = str(release_date) if release_date else None
        items.append(resp)
    return WatchlistResponse(
        user_id=user_id,
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )
