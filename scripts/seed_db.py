"""Seed PostgreSQL with processed movie data, users, and ratings."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from cinematch.config import get_settings


def seed_database(processed_dir: str | None = None) -> None:
    settings = get_settings()
    processed_dir = Path(processed_dir or settings.data_processed_dir)

    engine = create_engine(settings.database_url_sync, pool_size=5, echo=False)

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

    if embeddings is not None and len(embeddings) != len(movies):
        raise ValueError(f"Mismatch: {len(movies)} movies vs {len(embeddings)} embeddings")

    print(f"  Movies: {len(movies):,}")
    print(f"  Ratings: {len(ratings):,}")
    print(f"  Embeddings: {'loaded' if embeddings is not None else 'skipped'}")

    with Session(engine) as session:
        print("\nClearing existing data...")
        session.execute(text("TRUNCATE recommendations_cache, ratings, users, movies RESTART IDENTITY CASCADE"))
        session.commit()

        # --- Insert movies ---
        print("Inserting movies...")
        batch_size = 1000
        for start in range(0, len(movies), batch_size):
            end = min(start + batch_size, len(movies))
            batch = movies.iloc[start:end]
            for i, (_, row) in enumerate(batch.iterrows()):
                emb = embeddings[start + i].tolist() if embeddings is not None else None
                session.execute(
                    text("""
                        INSERT INTO movies (id, tmdb_id, imdb_id, movielens_id, title, overview,
                            genres, keywords, cast_names, director, release_date,
                            vote_average, vote_count, popularity, poster_path, embedding)
                        VALUES (:id, :tmdb_id, :imdb_id, :movielens_id, :title, :overview,
                            CAST(:genres AS jsonb), CAST(:keywords AS jsonb), CAST(:cast_names AS jsonb),
                            :director, :release_date,
                            :vote_average, :vote_count, :popularity, :poster_path, CAST(:embedding AS vector))
                    """),
                    {
                        "id": int(row["movie_id"]),
                        "tmdb_id": int(row["tmdb_id"]),
                        "imdb_id": str(row["imdb_id"]) if pd.notna(row.get("imdb_id")) else None,
                        "movielens_id": int(row["movielens_id"]),
                        "title": str(row["title"]),
                        "overview": str(row["overview"]) if pd.notna(row.get("overview")) else None,
                        "genres": json.dumps(list(row["genres"]) if hasattr(row["genres"], "__iter__") and not isinstance(row["genres"], str) else []),
                        "keywords": json.dumps(list(row["keywords"]) if hasattr(row["keywords"], "__iter__") and not isinstance(row["keywords"], str) else []),
                        "cast_names": json.dumps(list(row["cast_names"]) if hasattr(row["cast_names"], "__iter__") and not isinstance(row["cast_names"], str) else []),
                        "director": str(row["director"]) if pd.notna(row.get("director")) else None,
                        "release_date": row["release_date"].date() if pd.notna(row.get("release_date")) else None,
                        "vote_average": float(row["vote_average"]),
                        "vote_count": int(row["vote_count"]),
                        "popularity": float(row["popularity"]),
                        "poster_path": str(row["poster_path"]) if pd.notna(row.get("poster_path")) else None,
                        "embedding": str(emb) if emb is not None else None,
                    },
                )
            session.commit()
            if (end % 5000 == 0) or end == len(movies):
                print(f"  Movies: {end:,}/{len(movies):,}")

        session.execute(text(f"SELECT setval('movies_id_seq', {int(movies['movie_id'].max())})"))
        session.commit()

        # --- Insert users ---
        print("Inserting users...")
        unique_users = sorted(ratings["user_id"].unique())
        batch_size = 10000
        for start in range(0, len(unique_users), batch_size):
            end = min(start + batch_size, len(unique_users))
            batch = unique_users[start:end]
            values = ", ".join(f"({uid}, {uid})" for uid in batch)
            session.execute(text(f"INSERT INTO users (id, movielens_id) VALUES {values}"))
            session.commit()
            if (end % 50000 == 0) or end == len(unique_users):
                print(f"  Users: {end:,}/{len(unique_users):,}")

        session.execute(text(f"SELECT setval('users_id_seq', {max(unique_users)})"))
        session.commit()

        # --- Insert ratings ---
        print("Inserting ratings...")
        batch_size = 50000
        total = len(ratings)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch = ratings.iloc[start:end]
            values_parts = []
            for _, row in batch.iterrows():
                ts = row["timestamp"]
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, pd.Timestamp) else str(ts)
                scaled_rating = int(float(row['rating']) * 2)
                values_parts.append(
                    f"({int(row['user_id'])}, {int(row['movie_id'])}, {scaled_rating}, '{ts_str}')"
                )
            session.execute(
                text(f"INSERT INTO ratings (user_id, movie_id, rating, timestamp) VALUES {', '.join(values_parts)}")
            )
            session.commit()
            if (end % 500000 == 0) or end == total:
                print(f"  Ratings: {end:,}/{total:,}")

        # --- IVFFlat vector index ---
        if embeddings is not None:
            print("Creating IVFFlat vector index...")
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_movies_embedding
                ON movies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
            """))
            session.commit()
            print("  Done.")

        # --- Verify ---
        mc = session.execute(text("SELECT count(*) FROM movies")).scalar()
        uc = session.execute(text("SELECT count(*) FROM users")).scalar()
        rc = session.execute(text("SELECT count(*) FROM ratings")).scalar()
        print(f"\n=== Seeding Complete ===")
        print(f"  Movies:  {mc:,}")
        print(f"  Users:   {uc:,}")
        print(f"  Ratings: {rc:,}")


if __name__ == "__main__":
    seed_database()
