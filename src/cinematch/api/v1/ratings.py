"""Rating API endpoints (nested under /users)."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import (
    get_cache_service,
    get_current_user,
    get_db,
    get_movie_service,
    get_rating_service,
    require_same_user,
)
from cinematch.config import get_settings
from cinematch.core.cache import CacheService
from cinematch.models.user import User
from cinematch.schemas.rating import (
    ImportResponse,
    ImportResultItem,
    ImportSource,
    RatingBulkCheckResponse,
    RatingCreate,
    RatingResponse,
    UserRatingsResponse,
)
from cinematch.services.csv_import import (
    parse_csv_content,
    resolve_movies_imdb,
    resolve_movies_letterboxd,
)
from cinematch.services.movie_service import MovieService
from cinematch.services.rating_service import RatingService

router = APIRouter()


@router.post(
    "/users/{user_id}/ratings/import",
    response_model=ImportResponse,
)
async def import_ratings(
    user_id: int,
    file: UploadFile = File(...),
    source: ImportSource = Query(default=ImportSource.AUTO),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rating_service: RatingService = Depends(get_rating_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    require_same_user(current_user.id, user_id)
    settings = get_settings()

    # Validate file size
    contents = await file.read()
    max_bytes = settings.import_max_file_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.import_max_file_size_mb}MB.",
        )

    # Decode CSV content
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = contents.decode("latin-1")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=422, detail="Could not decode file. Use UTF-8 encoding."
            )

    if not text.strip():
        raise HTTPException(status_code=422, detail="CSV file is empty.")

    # Parse CSV
    try:
        parsed_rows, detected_source = parse_csv_content(text, source.value)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not parsed_rows:
        raise HTTPException(status_code=422, detail="No valid ratings found in CSV.")

    # Enforce row limit
    if len(parsed_rows) > settings.import_max_rows:
        raise HTTPException(
            status_code=422,
            detail=f"Too many rows ({len(parsed_rows)}). Maximum is {settings.import_max_rows}.",
        )

    # Resolve movie IDs
    if detected_source == "imdb":
        resolved = await resolve_movies_imdb(parsed_rows, db)
    else:
        resolved = await resolve_movies_letterboxd(parsed_rows, db)

    # Split into found and not-found
    to_import = [r for r in resolved if r["movie_id"] is not None]
    not_found = [r for r in resolved if r["movie_id"] is None]

    # Check which movies the user already rated (to distinguish imported vs updated)
    existing_movie_ids: set[int] = set()
    if to_import:
        movie_ids = [r["movie_id"] for r in to_import]
        existing_ratings = await rating_service.bulk_check(user_id, movie_ids, db)
        existing_movie_ids = set(existing_ratings.keys())

    # Bulk import matched ratings
    counts = {"imported": 0, "updated": 0}
    if to_import:
        counts = await rating_service.import_ratings(
            user_id,
            [{"movie_id": r["movie_id"], "rating": r["scaled_rating"]} for r in to_import],
            db,
        )

    # Invalidate cache
    if cache is not None and to_import:
        try:
            await cache.invalidate_user_recs(user_id)
        except Exception:  # noqa: BLE001
            pass

    # Build result items
    results: list[ImportResultItem] = []
    for r in to_import:
        status = "updated" if r["movie_id"] in existing_movie_ids else "imported"
        results.append(
            ImportResultItem(
                title=r["title"],
                year=r.get("year"),
                original_rating=r["original_rating"],
                scaled_rating=r["scaled_rating"],
                movie_id=r["movie_id"],
                status=status,
            )
        )
    for r in not_found:
        results.append(
            ImportResultItem(
                title=r["title"],
                year=r.get("year"),
                original_rating=r["original_rating"],
                scaled_rating=r["scaled_rating"],
                movie_id=None,
                status="not_found",
            )
        )

    return ImportResponse(
        user_id=user_id,
        source=detected_source,
        total_rows=len(resolved),
        imported=counts["imported"],
        updated=counts["updated"],
        not_found=len(not_found),
        results=results,
    )


@router.get("/users/{user_id}/ratings/export")
async def export_ratings(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rating_service: RatingService = Depends(get_rating_service),
):
    require_same_user(current_user.id, user_id)
    rows = await rating_service.export_ratings(user_id, db)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["movie_id", "title", "imdb_id", "tmdb_id", "rating", "timestamp"])
    for movie_id, title, imdb_id, tmdb_id, rating, timestamp in rows:
        writer.writerow([movie_id, title, imdb_id or "", tmdb_id, rating, timestamp.isoformat()])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cinematch_ratings_{user_id}.csv"},
    )


@router.post(
    "/users/{user_id}/ratings",
    response_model=RatingResponse,
    status_code=201,
)
async def add_rating(
    user_id: int,
    body: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    rating_service: RatingService = Depends(get_rating_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    require_same_user(current_user.id, user_id)
    movie = await movie_service.get_by_id(body.movie_id, db)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    rating = await rating_service.add_rating(user_id, body.movie_id, body.rating, db)

    # Invalidate cached recommendations for this user
    if cache is not None:
        try:
            await cache.invalidate_user_recs(user_id)
        except Exception:  # noqa: BLE001
            pass  # Cache failure should not break the request

    resp = RatingResponse.model_validate(rating)
    resp.movie_title = movie.title
    return resp


@router.get("/users/{user_id}/ratings/check", response_model=RatingBulkCheckResponse)
async def bulk_check_ratings(
    user_id: int,
    movie_ids: str = Query(..., description="Comma-separated movie IDs"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rating_service: RatingService = Depends(get_rating_service),
):
    require_same_user(current_user.id, user_id)
    id_list = [int(x.strip()) for x in movie_ids.split(",") if x.strip()]
    ratings = await rating_service.bulk_check(user_id, id_list, db)
    return RatingBulkCheckResponse(ratings=ratings)


@router.get("/users/{user_id}/ratings", response_model=UserRatingsResponse)
async def get_user_ratings(
    user_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rating_service: RatingService = Depends(get_rating_service),
):
    require_same_user(current_user.id, user_id)
    rows, total = await rating_service.get_user_ratings(user_id, db, offset=offset, limit=limit)
    ratings = []
    for rating, movie_title in rows:
        r = RatingResponse.model_validate(rating)
        r.movie_title = movie_title
        ratings.append(r)
    return UserRatingsResponse(
        user_id=user_id,
        ratings=ratings,
        total=total,
        offset=offset,
        limit=limit,
    )
