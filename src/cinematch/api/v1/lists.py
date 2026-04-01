"""API endpoints for custom user lists."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_db, get_movie_service, get_user_list_service
from cinematch.schemas.user_list import (
    PopularListsResponse,
    UserListCreate,
    UserListDetailResponse,
    UserListItemAdd,
    UserListItemReorder,
    UserListItemResponse,
    UserListResponse,
    UserListsResponse,
    UserListUpdate,
)
from cinematch.services.movie_service import MovieService
from cinematch.services.user_list_service import UserListService

router = APIRouter()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _list_summary(ul, movie_count: int, preview_posters: list[str]) -> UserListResponse:
    return UserListResponse(
        id=ul.id,
        user_id=ul.user_id,
        name=ul.name,
        description=ul.description,
        is_public=ul.is_public,
        movie_count=movie_count,
        preview_posters=preview_posters,
        created_at=ul.created_at,
        updated_at=ul.updated_at,
    )


def _item_response(item, title, poster_path, genres, vote_average, release_date):
    resp = UserListItemResponse.model_validate(item)
    resp.movie_title = title
    resp.poster_path = poster_path
    resp.genres = genres or []
    resp.vote_average = vote_average or 0.0
    resp.release_date = str(release_date) if release_date else None
    return resp


# ------------------------------------------------------------------
# List CRUD
# ------------------------------------------------------------------


@router.post("/users/{user_id}/lists", response_model=UserListResponse, status_code=201)
async def create_list(
    user_id: int,
    body: UserListCreate,
    db: AsyncSession = Depends(get_db),
    list_service: UserListService = Depends(get_user_list_service),
):
    """Create a new user list."""
    ul = await list_service.create_list(user_id, body.name, body.description, body.is_public, db)
    return UserListResponse(
        id=ul.id,
        user_id=ul.user_id,
        name=ul.name,
        description=ul.description,
        is_public=ul.is_public,
        movie_count=0,
        preview_posters=[],
        created_at=ul.created_at,
        updated_at=ul.updated_at,
    )


@router.get("/users/{user_id}/lists", response_model=UserListsResponse)
async def get_user_lists(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    list_service: UserListService = Depends(get_user_list_service),
):
    """Get all lists for a user."""
    rows = await list_service.get_user_lists(user_id, db)
    lists_ = [_list_summary(ul, mc, pp) for ul, mc, pp in rows]
    return UserListsResponse(user_id=user_id, lists=lists_, total=len(lists_))


@router.get("/lists/popular", response_model=PopularListsResponse)
async def get_popular_lists(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    list_service: UserListService = Depends(get_user_list_service),
):
    """Browse popular public lists."""
    rows, total = await list_service.get_popular_lists(db, offset=offset, limit=limit)
    lists_ = [_list_summary(ul, mc, pp) for ul, mc, pp in rows]
    return PopularListsResponse(lists=lists_, total=total, offset=offset, limit=limit)


@router.get("/lists/{list_id}", response_model=UserListDetailResponse)
async def get_list(
    list_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    list_service: UserListService = Depends(get_user_list_service),
):
    """Get a single list with its items."""
    result = await list_service.get_list(list_id, db, offset=offset, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="List not found")
    ul, rows, total = result
    items = [
        _item_response(item, title, pp, genres, va, rd) for item, title, pp, genres, va, rd in rows
    ]
    return UserListDetailResponse(
        id=ul.id,
        user_id=ul.user_id,
        name=ul.name,
        description=ul.description,
        is_public=ul.is_public,
        movie_count=total,
        items=items,
        total=total,
        offset=offset,
        limit=limit,
        created_at=ul.created_at,
        updated_at=ul.updated_at,
    )


@router.patch("/users/{user_id}/lists/{list_id}", response_model=UserListResponse)
async def update_list(
    user_id: int,
    list_id: int,
    body: UserListUpdate,
    db: AsyncSession = Depends(get_db),
    list_service: UserListService = Depends(get_user_list_service),
):
    """Update list metadata."""
    ul = await list_service.update_list(
        user_id,
        list_id,
        db,
        name=body.name,
        description=body.description,
        is_public=body.is_public,
    )
    if ul is None:
        raise HTTPException(status_code=404, detail="List not found or not owned by user")
    # Get counts for response
    rows = await list_service.get_user_lists(user_id, db)
    for r_ul, mc, pp in rows:
        if r_ul.id == list_id:
            return _list_summary(r_ul, mc, pp)
    return UserListResponse(
        id=ul.id,
        user_id=ul.user_id,
        name=ul.name,
        description=ul.description,
        is_public=ul.is_public,
        movie_count=0,
        preview_posters=[],
        created_at=ul.created_at,
        updated_at=ul.updated_at,
    )


@router.delete("/users/{user_id}/lists/{list_id}", status_code=204)
async def delete_list(
    user_id: int,
    list_id: int,
    db: AsyncSession = Depends(get_db),
    list_service: UserListService = Depends(get_user_list_service),
):
    """Delete a list and all its items."""
    deleted = await list_service.delete_list(user_id, list_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="List not found or not owned by user")


# ------------------------------------------------------------------
# Item operations
# ------------------------------------------------------------------


@router.post(
    "/users/{user_id}/lists/{list_id}/items",
    response_model=UserListItemResponse,
    status_code=201,
)
async def add_item_to_list(
    user_id: int,
    list_id: int,
    body: UserListItemAdd,
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    list_service: UserListService = Depends(get_user_list_service),
):
    """Add a movie to a list."""
    movie = await movie_service.get_by_id(body.movie_id, db)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    item = await list_service.add_item(user_id, list_id, body.movie_id, db)
    if item is None:
        raise HTTPException(status_code=404, detail="List not found or not owned by user")

    resp = UserListItemResponse.model_validate(item)
    resp.movie_title = movie.title
    resp.poster_path = movie.poster_path
    resp.genres = movie.genres or []
    resp.vote_average = movie.vote_average
    resp.release_date = str(movie.release_date) if movie.release_date else None
    return resp


@router.delete("/users/{user_id}/lists/{list_id}/items/{movie_id}", status_code=204)
async def remove_item_from_list(
    user_id: int,
    list_id: int,
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    list_service: UserListService = Depends(get_user_list_service),
):
    """Remove a movie from a list."""
    removed = await list_service.remove_item(user_id, list_id, movie_id, db)
    if not removed:
        raise HTTPException(status_code=404, detail="List or item not found")


@router.put("/users/{user_id}/lists/{list_id}/items/reorder", status_code=200)
async def reorder_list_items(
    user_id: int,
    list_id: int,
    body: UserListItemReorder,
    db: AsyncSession = Depends(get_db),
    list_service: UserListService = Depends(get_user_list_service),
):
    """Reorder items in a list."""
    success = await list_service.reorder_items(user_id, list_id, body.movie_ids, db)
    if not success:
        raise HTTPException(status_code=404, detail="List not found or not owned by user")
    return {"status": "ok"}
