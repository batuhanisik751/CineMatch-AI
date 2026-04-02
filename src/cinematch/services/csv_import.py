"""CSV import parsing and movie resolution for Letterboxd and IMDb exports."""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING

from sqlalchemy import extract, func, select

from cinematch.models.movie import Movie

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def detect_source(headers: list[str]) -> str:
    """Auto-detect CSV source from column headers."""
    header_set = set(headers)
    if "Const" in header_set and "Your Rating" in header_set:
        return "imdb"
    if "Name" in header_set and "Rating" in header_set and "Letterboxd URI" in header_set:
        return "letterboxd"
    raise ValueError("Unrecognized CSV format. Expected Letterboxd or IMDb export columns.")


def parse_letterboxd_csv(reader: csv.DictReader) -> list[dict]:
    """Parse Letterboxd ratings CSV. Scale 0.5-5.0 → 1-10."""
    rows: list[dict] = []
    for row in reader:
        raw = row.get("Rating", "").strip()
        if not raw:
            continue
        try:
            original = float(raw)
        except ValueError:
            continue
        scaled = max(1, min(10, round(original * 2)))
        year_str = row.get("Year", "").strip()
        year = int(year_str) if year_str.isdigit() else None
        rows.append(
            {
                "title": row.get("Name", "").strip(),
                "year": year,
                "original_rating": original,
                "scaled_rating": scaled,
            }
        )
    return rows


def parse_imdb_csv(reader: csv.DictReader) -> list[dict]:
    """Parse IMDb ratings CSV. Rating is already 1-10."""
    rows: list[dict] = []
    for row in reader:
        raw = row.get("Your Rating", "").strip()
        if not raw:
            continue
        try:
            original = int(raw)
        except ValueError:
            continue
        scaled = max(1, min(10, original))
        imdb_id = row.get("Const", "").strip()
        if not imdb_id:
            continue
        year_str = row.get("Year", "").strip()
        year = int(year_str) if year_str.isdigit() else None
        rows.append(
            {
                "imdb_id": imdb_id,
                "title": row.get("Title", "").strip(),
                "year": year,
                "original_rating": original,
                "scaled_rating": scaled,
            }
        )
    return rows


async def resolve_movies_imdb(
    parsed_rows: list[dict],
    db: AsyncSession,
) -> list[dict]:
    """Resolve IMDb IDs to internal movie IDs."""
    imdb_ids = list({r["imdb_id"] for r in parsed_rows})
    if not imdb_ids:
        return [{**r, "movie_id": None, "status": "not_found"} for r in parsed_rows]

    result = await db.execute(select(Movie.id, Movie.imdb_id).where(Movie.imdb_id.in_(imdb_ids)))
    lookup = {row[1]: row[0] for row in result.all()}

    resolved = []
    for r in parsed_rows:
        movie_id = lookup.get(r["imdb_id"])
        resolved.append(
            {
                **r,
                "movie_id": movie_id,
                "status": "not_found" if movie_id is None else "pending",
            }
        )
    return resolved


async def resolve_movies_letterboxd(
    parsed_rows: list[dict],
    db: AsyncSession,
) -> list[dict]:
    """Resolve Letterboxd movies by title + year matching."""
    titles = list({r["title"].lower() for r in parsed_rows if r["title"]})
    if not titles:
        return [{**r, "movie_id": None, "status": "not_found"} for r in parsed_rows]

    result = await db.execute(
        select(
            Movie.id,
            Movie.title,
            extract("year", Movie.release_date).label("yr"),
            Movie.popularity,
        ).where(func.lower(Movie.title).in_(titles))
    )
    rows_db = result.all()

    # Build lookup: (lower_title, year) -> (movie_id, popularity)
    # On ambiguity, keep the movie with highest popularity
    lookup: dict[tuple[str, int | None], tuple[int, float]] = {}
    for movie_id, title, yr, popularity in rows_db:
        year_int = int(yr) if yr is not None else None
        key = (title.lower(), year_int)
        existing = lookup.get(key)
        if existing is None or (popularity or 0) > existing[1]:
            lookup[key] = (movie_id, popularity or 0)

    resolved = []
    for r in parsed_rows:
        key = (r["title"].lower(), r.get("year"))
        match = lookup.get(key)
        movie_id = match[0] if match else None
        resolved.append(
            {
                **r,
                "movie_id": movie_id,
                "status": "not_found" if movie_id is None else "pending",
            }
        )
    return resolved


def parse_csv_content(content: str, source: str) -> tuple[list[dict], str]:
    """Parse CSV content string and return (parsed_rows, detected_source)."""
    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []

    if source == "auto":
        source = detect_source(headers)

    if source == "imdb":
        return parse_imdb_csv(reader), source
    return parse_letterboxd_csv(reader), source
