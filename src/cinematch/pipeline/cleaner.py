"""Clean and join MovieLens + TMDb datasets into unified parquet files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from tqdm import tqdm

from cinematch.config import get_settings

tqdm.pandas()


def load_tmdb(tmdb_path: Path) -> pd.DataFrame:
    """Load and clean TMDB_all_movies.csv (single-file format)."""
    print(f"Loading {tmdb_path.name}...")
    df = pd.read_csv(tmdb_path, low_memory=False)

    # Clean ID column (integers, no corruption in this dataset)
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df = df.dropna(subset=["id"])
    df["id"] = df["id"].astype(int)
    df = df.drop_duplicates(subset="id", keep="first")

    # Genres: comma-separated text -> list of strings
    df["genres"] = (
        df["genres"]
        .fillna("")
        .apply(
            lambda x: (
                [g.strip() for g in x.split(",") if g.strip()]
                if isinstance(x, str) and x.strip()
                else []
            )
        )
    )

    # Cast: comma-separated names -> top 5 list
    df["cast_names"] = (
        df["cast"]
        .fillna("")
        .apply(
            lambda x: (
                [c.strip() for c in x.split(",")][:5] if isinstance(x, str) and x.strip() else []
            )
        )
    )

    # Director: plain text (take first if comma-separated for multiple directors)
    df["director"] = (
        df["director"]
        .fillna("")
        .apply(lambda x: x.split(",")[0].strip() if isinstance(x, str) and x.strip() else None)
    )

    # Parse release_date
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")

    # Ensure numeric columns
    for col in ["vote_average", "vote_count", "popularity"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["vote_count"] = df["vote_count"].astype(int)

    # Language: plain ISO 639-1 code, fill missing
    df["original_language"] = df["original_language"].fillna("")

    # Runtime: integer minutes, keep NaN for missing
    df["runtime"] = pd.to_numeric(df["runtime"], errors="coerce").astype("Int64")

    # Select and rename columns
    result = df[
        [
            "id",
            "imdb_id",
            "title",
            "overview",
            "genres",
            "cast_names",
            "director",
            "release_date",
            "vote_average",
            "vote_count",
            "popularity",
            "poster_path",
            "original_language",
            "runtime",
        ]
    ].copy()
    result = result.rename(columns={"id": "tmdb_id"})

    print(f"  Loaded {len(result):,} movies from TMDb metadata.")
    return result


def load_tags(ml_dir: Path) -> pd.DataFrame:
    """Load MovieLens tags.csv and aggregate unique tags per movie as keyword substitute."""
    print("Loading tags.csv...")
    df = pd.read_csv(ml_dir / "tags.csv")

    # Group by movieId, collect unique lowercased tags (preserve insertion order)
    tags_agg = (
        df.groupby("movieId")["tag"]
        .apply(
            lambda tags: list(
                dict.fromkeys(t.strip().lower() for t in tags if isinstance(t, str) and t.strip())
            )
        )
        .reset_index()
    )
    tags_agg = tags_agg.rename(columns={"movieId": "movielens_id", "tag": "keywords"})
    print(f"  Aggregated tags for {len(tags_agg):,} movies.")
    return tags_agg


def load_movielens_links(ml_dir: Path) -> pd.DataFrame:
    """Load MovieLens links.csv (movieId <-> tmdbId mapping)."""
    print("Loading links.csv...")
    df = pd.read_csv(ml_dir / "links.csv")
    df["tmdbId"] = pd.to_numeric(df["tmdbId"], errors="coerce")
    df = df.dropna(subset=["tmdbId"])
    df["tmdbId"] = df["tmdbId"].astype(int)
    df = df.rename(columns={"movieId": "movielens_id", "tmdbId": "tmdb_id", "imdbId": "imdb_id_ml"})
    print(f"  Loaded {len(df):,} movie links.")
    return df


def load_ratings(ml_dir: Path) -> pd.DataFrame:
    """Load MovieLens ratings.csv."""
    print("Loading ratings.csv (~32M rows, this may take a moment)...")
    df = pd.read_csv(ml_dir / "ratings.csv")
    df = df.rename(columns={"userId": "user_id", "movieId": "movielens_id"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    print(f"  Loaded {len(df):,} ratings.")
    return df


def clean_and_join(
    raw_dir: str | None = None,
    processed_dir: str | None = None,
    min_ratings_per_movie: int = 5,
    min_ratings_per_user: int = 20,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the full cleaning and joining pipeline.

    Returns (movies_df, ratings_df, id_mapping_df).
    """
    settings = get_settings()
    raw_dir = Path(raw_dir or settings.data_raw_dir)
    processed_dir = Path(processed_dir or settings.data_processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    ml_dir = raw_dir / "ml-32m"
    tmdb_path = raw_dir / "TMDB_all_movies.csv"

    # Validate input files exist
    for path, name in [
        (ml_dir / "ratings.csv", "MovieLens ratings"),
        (ml_dir / "links.csv", "MovieLens links"),
        (ml_dir / "tags.csv", "MovieLens tags"),
        (tmdb_path, "TMDb metadata"),
    ]:
        if not path.exists():
            raise FileNotFoundError(f"{name} not found at {path}. Run download_data.py first.")

    # --- Load all sources ---
    movies = load_tmdb(tmdb_path)
    links = load_movielens_links(ml_dir)
    tags = load_tags(ml_dir)
    ratings = load_ratings(ml_dir)

    # --- Join with MovieLens links (to get movielens_id) ---
    print("\nJoining TMDb metadata with MovieLens links...")
    movies = movies.merge(links[["movielens_id", "tmdb_id"]], on="tmdb_id", how="inner")
    print(f"  Movies with MovieLens IDs: {len(movies):,}")

    # --- Join with tags (keyword substitute) ---
    print("Joining with MovieLens tags as keywords...")
    movies = movies.merge(tags, on="movielens_id", how="left")

    # Fill NaN lists with empty lists
    for col in ["keywords", "cast_names"]:
        movies[col] = movies[col].apply(lambda x: x if isinstance(x, list) else [])

    # --- Filter: drop movies without overview ---
    before = len(movies)
    movies = movies.dropna(subset=["overview"])
    movies = movies[movies["overview"].str.strip().str.len() > 0]
    print(f"  Dropped {before - len(movies)} movies without overview. Remaining: {len(movies):,}")

    # --- Filter: drop movies with < min_ratings ---
    rating_counts = ratings.groupby("movielens_id").size()
    popular_movies = set(rating_counts[rating_counts >= min_ratings_per_movie].index)
    before = len(movies)
    movies = movies[movies["movielens_id"].isin(popular_movies)]
    dropped = before - len(movies)
    print(
        f"  Dropped {dropped} movies with <{min_ratings_per_movie} ratings."
        f" Remaining: {len(movies):,}"
    )

    # --- Filter ratings to only include movies we kept ---
    valid_movielens_ids = set(movies["movielens_id"])
    before = len(ratings)
    ratings = ratings[ratings["movielens_id"].isin(valid_movielens_ids)]
    print(f"  Filtered ratings to valid movies: {before:,} -> {len(ratings):,}")

    # --- Filter: keep users with >= min_ratings ---
    user_counts = ratings.groupby("user_id").size()
    active_users = set(user_counts[user_counts >= min_ratings_per_user].index)
    before = len(ratings)
    ratings = ratings[ratings["user_id"].isin(active_users)]
    print(f"  Kept users with >={min_ratings_per_user} ratings: {before:,} -> {len(ratings):,}")

    # --- Create sequential IDs ---
    movies = movies.reset_index(drop=True)
    movies["movie_id"] = range(1, len(movies) + 1)

    # --- Build ID mapping ---
    id_mapping = movies[["movie_id", "movielens_id", "tmdb_id"]].copy()

    # --- Map ratings to new movie_id ---
    ml_to_id = dict(zip(movies["movielens_id"], movies["movie_id"]))
    ratings["movie_id"] = ratings["movielens_id"].map(ml_to_id)
    ratings = ratings.dropna(subset=["movie_id"])
    ratings["movie_id"] = ratings["movie_id"].astype(int)

    # --- Remap user IDs to sequential ---
    unique_users = sorted(ratings["user_id"].unique())
    user_id_map = {old: new for new, old in enumerate(unique_users, start=1)}
    ratings["original_user_id"] = ratings["user_id"]
    ratings["user_id"] = ratings["user_id"].map(user_id_map)

    # --- Save outputs ---
    print(f"\nSaving to {processed_dir}/...")

    movies_out = movies[
        [
            "movie_id",
            "tmdb_id",
            "imdb_id",
            "movielens_id",
            "title",
            "overview",
            "genres",
            "keywords",
            "cast_names",
            "director",
            "release_date",
            "vote_average",
            "vote_count",
            "popularity",
            "poster_path",
            "original_language",
            "runtime",
        ]
    ]
    movies_out.to_parquet(processed_dir / "movies_clean.parquet", index=False)
    print(f"  movies_clean.parquet: {len(movies_out):,} rows")

    ratings_out = ratings[["user_id", "movie_id", "rating", "timestamp"]].copy()
    ratings_out.to_parquet(processed_dir / "ratings_clean.parquet", index=False)
    print(f"  ratings_clean.parquet: {len(ratings_out):,} rows")

    id_mapping.to_parquet(processed_dir / "id_mapping.parquet", index=False)
    print(f"  id_mapping.parquet: {len(id_mapping):,} rows")

    # Save user ID mapping for ALS
    user_mapping = pd.DataFrame(
        {"user_id": list(user_id_map.values()), "movielens_id": list(user_id_map.keys())}
    )
    user_mapping.to_parquet(processed_dir / "user_mapping.parquet", index=False)
    print(f"  user_mapping.parquet: {len(user_mapping):,} rows")

    print("\n[OK] Cleaning complete.")
    return movies_out, ratings_out, id_mapping


if __name__ == "__main__":
    clean_and_join()
