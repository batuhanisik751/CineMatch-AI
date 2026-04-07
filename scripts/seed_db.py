"""Seed PostgreSQL with processed movie data, users, and ratings.

Optimized for remote databases (Supabase): uses COPY protocol for ratings,
batch inserts for movies, and drops/rebuilds indexes during bulk load.
"""

from __future__ import annotations

import io
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from cinematch.config import get_settings

# ---------------------------------------------------------------------------
# Index / constraint management
# ---------------------------------------------------------------------------

# Indexes to drop before bulk insert and recreate after
RATINGS_INDEXES = [
    ("idx_ratings_user_id", "ratings", "user_id"),
    ("idx_ratings_movie_id", "ratings", "movie_id"),
    ("idx_ratings_timestamp", "ratings", "timestamp"),
]

MOVIES_INDEXES_BTREE = [
    ("idx_movies_tmdb_id", "movies", "tmdb_id"),
    ("idx_movies_movielens_id", "movies", "movielens_id"),
    ("idx_movies_imdb_id", "movies", "imdb_id"),
    ("idx_movies_original_language", "movies", "original_language"),
]

MOVIES_INDEXES_GIN = [
    ("idx_movies_genres", "movies", "genres", "jsonb_path_ops"),
    ("idx_movies_cast_names", "movies", "cast_names", "jsonb_path_ops"),
    ("idx_movies_keywords", "movies", "keywords", "jsonb_path_ops"),
]

# Trigram index (requires pg_trgm)
MOVIES_INDEX_TRGM = ("idx_movies_title_trgm", "movies", "title", "gin_trgm_ops")


def _drop_indexes(session: Session) -> None:
    """Drop indexes that slow down bulk inserts."""
    print("  Dropping indexes for bulk load...")
    for name, *_ in RATINGS_INDEXES + MOVIES_INDEXES_BTREE:
        session.execute(text(f"DROP INDEX IF EXISTS {name}"))
    for name, *_ in MOVIES_INDEXES_GIN:
        session.execute(text(f"DROP INDEX IF EXISTS {name}"))
    session.execute(text(f"DROP INDEX IF EXISTS {MOVIES_INDEX_TRGM[0]}"))
    # Drop constraints that slow down ratings insert
    session.execute(text("ALTER TABLE ratings DROP CONSTRAINT IF EXISTS uq_user_movie"))
    session.execute(text("ALTER TABLE ratings DROP CONSTRAINT IF EXISTS ck_rating_range"))
    session.commit()


def _rebuild_indexes(session: Session) -> None:
    """Rebuild all indexes after bulk load."""
    print("Rebuilding indexes...")
    t0 = time.time()

    # B-tree indexes on ratings
    for name, table, column in RATINGS_INDEXES:
        session.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({column})"))

    # B-tree indexes on movies
    for name, table, column in MOVIES_INDEXES_BTREE:
        session.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({column})"))

    # GIN indexes on movies
    for name, table, column, ops in MOVIES_INDEXES_GIN:
        session.execute(
            text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} USING gin ({column} {ops})")
        )

    # Trigram index
    name, table, column, ops = MOVIES_INDEX_TRGM
    session.execute(
        text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} USING gin ({column} {ops})")
    )

    # Rebuild constraints
    session.execute(
        text("ALTER TABLE ratings ADD CONSTRAINT uq_user_movie UNIQUE (user_id, movie_id)")
    )
    session.execute(
        text(
            "ALTER TABLE ratings ADD CONSTRAINT ck_rating_range "
            "CHECK (rating >= 1 AND rating <= 10)"
        )
    )
    session.commit()
    print(f"  Indexes rebuilt in {time.time() - t0:.0f}s")


# ---------------------------------------------------------------------------
# Movie insert helpers
# ---------------------------------------------------------------------------


def _escape_copy_field(val: str | None) -> str:
    """Escape a string value for PostgreSQL COPY text format."""
    if val is None:
        return r"\N"
    # Escape backslashes, tabs, newlines, carriage returns
    return val.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def _format_vector(arr: np.ndarray) -> str:
    """Format a numpy array as pgvector text: [0.1,0.2,...,0.384]."""
    return "[" + ",".join(f"{v:.8f}" for v in arr) + "]"


def _insert_movies_copy(
    session: Session, movies: pd.DataFrame, embeddings: np.ndarray | None
) -> None:
    """Insert movies using PostgreSQL COPY protocol for maximum speed."""
    print("Inserting movies (COPY protocol)...")
    t0 = time.time()
    total = len(movies)

    raw_conn = session.connection().connection
    cursor = raw_conn.cursor()

    columns = (
        "id, tmdb_id, imdb_id, movielens_id, title, overview, "
        "genres, keywords, cast_names, director, release_date, "
        "vote_average, vote_count, popularity, poster_path, original_language, "
        "runtime, tagline, budget, revenue, embedding"
    )

    batch_size = 5000
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = movies.iloc[start:end]

        buf = io.StringIO()
        for i, (_, row) in enumerate(batch.iterrows()):
            idx = start + i

            # Format each field for COPY text format (\N for NULL, tab-separated)
            movie_id = str(int(row["movie_id"]))
            tmdb_id = str(int(row["tmdb_id"]))
            imdb_id = _escape_copy_field(
                str(row["imdb_id"]) if pd.notna(row.get("imdb_id")) else None
            )
            movielens_id = str(int(row["movielens_id"]))
            title = _escape_copy_field(str(row["title"]))
            overview = _escape_copy_field(
                str(row["overview"]) if pd.notna(row.get("overview")) else None
            )

            genres = _escape_copy_field(
                json.dumps(
                    list(row["genres"])
                    if hasattr(row["genres"], "__iter__") and not isinstance(row["genres"], str)
                    else []
                )
            )
            keywords = _escape_copy_field(
                json.dumps(
                    list(row["keywords"])
                    if hasattr(row["keywords"], "__iter__") and not isinstance(row["keywords"], str)
                    else []
                )
            )
            cast_names = _escape_copy_field(
                json.dumps(
                    list(row["cast_names"])
                    if hasattr(row["cast_names"], "__iter__")
                    and not isinstance(row["cast_names"], str)
                    else []
                )
            )

            director = _escape_copy_field(
                str(row["director"]) if pd.notna(row.get("director")) else None
            )
            release_date = (
                row["release_date"].strftime("%Y-%m-%d")
                if pd.notna(row.get("release_date"))
                else r"\N"
            )
            vote_average = str(float(row["vote_average"]))
            vote_count = str(int(row["vote_count"]))
            popularity = str(float(row["popularity"]))
            poster_path = _escape_copy_field(
                str(row["poster_path"]) if pd.notna(row.get("poster_path")) else None
            )
            original_language = _escape_copy_field(
                str(row["original_language"])
                if pd.notna(row.get("original_language")) and row.get("original_language")
                else None
            )
            runtime = str(int(row["runtime"])) if pd.notna(row.get("runtime")) else r"\N"
            tagline = _escape_copy_field(
                str(row["tagline"]) if pd.notna(row.get("tagline")) and row.get("tagline") else None
            )
            budget = str(int(row["budget"])) if pd.notna(row.get("budget")) else r"\N"
            revenue = str(int(row["revenue"])) if pd.notna(row.get("revenue")) else r"\N"

            if embeddings is not None:
                embedding = _format_vector(embeddings[idx])
            else:
                embedding = r"\N"

            line = "\t".join(
                [
                    movie_id,
                    tmdb_id,
                    imdb_id,
                    movielens_id,
                    title,
                    overview,
                    genres,
                    keywords,
                    cast_names,
                    director,
                    release_date,
                    vote_average,
                    vote_count,
                    popularity,
                    poster_path,
                    original_language,
                    runtime,
                    tagline,
                    budget,
                    revenue,
                    embedding,
                ]
            )
            buf.write(line + "\n")

        buf.seek(0)
        cursor.copy_expert(
            f"COPY movies ({columns}) FROM STDIN WITH (FORMAT text)",
            buf,
        )
        raw_conn.commit()

        elapsed = time.time() - t0
        if (end % 5000 == 0) or end == total:
            print(f"  Movies: {end:,}/{total:,}  ({elapsed:.0f}s)")

    session.execute(text(f"SELECT setval('movies_id_seq', {int(movies['movie_id'].max())})"))
    session.commit()
    print(f"  Movies done in {time.time() - t0:.0f}s")


# ---------------------------------------------------------------------------
# User insert
# ---------------------------------------------------------------------------


def _insert_users(session: Session, ratings: pd.DataFrame) -> list:
    """Insert unique users. Returns sorted user ID list."""
    print("Inserting users...")
    t0 = time.time()
    unique_users = sorted(ratings["user_id"].unique())
    batch_size = 5000
    for start in range(0, len(unique_users), batch_size):
        end = min(start + batch_size, len(unique_users))
        batch = unique_users[start:end]
        values = ", ".join(f"({uid}, {uid})" for uid in batch)
        session.execute(text(f"INSERT INTO users (id, movielens_id) VALUES {values}"))
        session.commit()
        if (end % 20000 == 0) or end == len(unique_users):
            elapsed = time.time() - t0
            print(f"  Users: {end:,}/{len(unique_users):,}  ({elapsed:.0f}s)")

    session.execute(text(f"SELECT setval('users_id_seq', {max(unique_users)})"))
    session.commit()
    print(f"  Users done in {time.time() - t0:.0f}s")
    return unique_users


# ---------------------------------------------------------------------------
# Ratings insert — COPY protocol (10-20x faster than INSERT for bulk data)
# ---------------------------------------------------------------------------


def _insert_ratings_copy(engine, ratings: pd.DataFrame) -> None:
    """Insert ratings using PostgreSQL COPY protocol via psycopg2.

    Uses a fresh connection per batch to avoid SSL timeouts on remote databases.
    COPY streams data directly into the table without per-row SQL parsing,
    constraint checking overhead, or WAL amplification from individual INSERTs.
    """
    print("Inserting ratings (COPY protocol)...")
    t0 = time.time()
    total = len(ratings)

    # Pre-compute the scaled rating column vectorized (0.5-5.0 → 1-10)
    ratings = ratings.copy()
    ratings["scaled_rating"] = (ratings["rating"] * 2).astype(int)

    # Format timestamps as strings
    ratings["ts_str"] = pd.to_datetime(ratings["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    batch_size = 100_000
    max_retries = 3
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = ratings.iloc[start:end]

        # Build a tab-separated buffer using vectorized pandas to_csv
        buf = io.StringIO()
        batch[["user_id", "movie_id", "scaled_rating", "ts_str"]].to_csv(
            buf, sep="\t", header=False, index=False, lineterminator="\n"
        )

        # Use a fresh raw connection per batch to avoid SSL timeout
        for attempt in range(1, max_retries + 1):
            try:
                raw_conn = engine.raw_connection()
                cursor = raw_conn.cursor()
                buf.seek(0)
                cursor.copy_expert(
                    "COPY ratings (user_id, movie_id, rating, timestamp) "
                    "FROM STDIN WITH (FORMAT text)",
                    buf,
                )
                raw_conn.commit()
                cursor.close()
                raw_conn.close()
                break
            except Exception as e:
                if attempt < max_retries:
                    print(f"  Batch {start:,}-{end:,} failed (attempt {attempt}): {e}")
                    print("  Retrying in 5s...")
                    time.sleep(5)
                else:
                    raise

        elapsed = time.time() - t0
        rate = end / elapsed if elapsed > 0 else 0
        if (end % 100_000 == 0) or end == total:
            print(f"  Ratings: {end:,}/{total:,}  ({elapsed:.0f}s, {rate:,.0f} rows/s)")

    print(f"  Ratings done in {time.time() - t0:.0f}s")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def seed_database(processed_dir: str | None = None, max_users: int | None = None) -> None:
    settings = get_settings()
    processed_dir = Path(processed_dir or settings.data_processed_dir)

    engine = create_engine(settings.database_url_sync.get_secret_value(), pool_size=5, echo=False)

    # Load data
    print("Loading processed data...")
    movies = pd.read_parquet(processed_dir / "movies_clean.parquet")
    ratings = pd.read_parquet(processed_dir / "ratings_clean.parquet")

    embeddings_path = processed_dir / "embeddings.npy"
    embeddings = np.load(embeddings_path) if embeddings_path.exists() else None

    # Deduplicate movies on tmdb_id (data may have dupes from joins)
    dup_mask = movies.duplicated(subset="tmdb_id", keep="first")
    if dup_mask.any():
        dup_count = dup_mask.sum()
        keep_indices = (~dup_mask).values
        movies = movies[keep_indices].reset_index(drop=True)
        if embeddings is not None:
            embeddings = embeddings[keep_indices]
        print(f"  Removed {dup_count} duplicate tmdb_ids.")

    # Filter ratings to only include movies that survived dedup
    valid_movie_ids = set(movies["movie_id"])
    ratings = ratings[ratings["movie_id"].isin(valid_movie_ids)].copy()

    # Limit to top N most active users to fit in free-tier storage (Supabase 500 MB)
    if max_users is not None:
        user_counts = ratings.groupby("user_id").size()
        top_users = set(user_counts.nlargest(max_users).index)
        original_count = len(ratings)
        ratings = ratings[ratings["user_id"].isin(top_users)].copy()
        print(
            f"  Filtered to top {max_users:,} users: "
            f"{len(ratings):,} ratings (was {original_count:,})"
        )

    if embeddings is not None and len(embeddings) != len(movies):
        raise ValueError(f"Mismatch: {len(movies)} movies vs {len(embeddings)} embeddings")

    print(f"  Movies: {len(movies):,}")
    print(f"  Ratings: {len(ratings):,}")
    print(f"  Embeddings: {'loaded' if embeddings is not None else 'skipped'}")

    with Session(engine) as session:
        print("\nClearing existing data...")
        session.execute(
            text("TRUNCATE recommendations_cache, ratings, users, movies RESTART IDENTITY CASCADE")
        )
        session.commit()

        # Drop indexes for faster bulk insert
        _drop_indexes(session)

        # --- Insert movies (COPY protocol) ---
        _insert_movies_copy(session, movies, embeddings)

        # --- Insert users ---
        _insert_users(session, ratings)

        # --- Insert ratings (COPY protocol, fresh connections per batch) ---
        _insert_ratings_copy(engine, ratings)

        # --- Rebuild indexes and constraints ---
        _rebuild_indexes(session)

        # --- IVFFlat vector index (always built post-load) ---
        if embeddings is not None:
            print("Creating IVFFlat vector index...")
            session.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_movies_embedding
                ON movies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
            """)
            )
            session.commit()
            print("  Done.")

        # --- Verify ---
        mc = session.execute(text("SELECT count(*) FROM movies")).scalar()
        uc = session.execute(text("SELECT count(*) FROM users")).scalar()
        rc = session.execute(text("SELECT count(*) FROM ratings")).scalar()
        print("\n=== Seeding Complete ===")
        print(f"  Movies:  {mc:,}")
        print(f"  Users:   {uc:,}")
        print(f"  Ratings: {rc:,}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed the database with movie data")
    parser.add_argument(
        "--max-users",
        type=int,
        default=None,
        help="Limit to top N most active users (by rating count) to reduce storage",
    )
    args = parser.parse_args()
    seed_database(max_users=args.max_users)
