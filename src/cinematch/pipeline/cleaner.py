"""Clean and join MovieLens + TMDb datasets into unified parquet files."""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from cinematch.config import get_settings

tqdm.pandas()


def _safe_literal_eval(val: str) -> list:
    """Parse Python-literal JSON strings (e.g., TMDb genres/keywords columns)."""
    if not isinstance(val, str) or not val.strip():
        return []
    try:
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return []


def _extract_names(items: list[dict]) -> list[str]:
    """Extract 'name' values from a list of dicts."""
    if not isinstance(items, list):
        return []
    return [item["name"] for item in items if isinstance(item, dict) and "name" in item]


def _extract_top_cast(credits_str: str, top_n: int = 5) -> list[str]:
    """Extract top N cast member names from credits JSON string."""
    parsed = _safe_literal_eval(credits_str)
    return [p["name"] for p in parsed[:top_n] if isinstance(p, dict) and "name" in p]


def _extract_director(crew_str: str) -> str | None:
    """Extract director name from crew JSON string."""
    parsed = _safe_literal_eval(crew_str)
    for member in parsed:
        if isinstance(member, dict) and member.get("job") == "Director":
            return member.get("name")
    return None


def load_tmdb_metadata(tmdb_dir: Path) -> pd.DataFrame:
    """Load and clean TMDb movies_metadata.csv."""
    print("Loading movies_metadata.csv...")
    df = pd.read_csv(tmdb_dir / "movies_metadata.csv", low_memory=False)

    # Fix bad rows: some have date strings in the 'id' column
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df = df.dropna(subset=["id"])
    df["id"] = df["id"].astype(int)

    # Remove duplicates
    df = df.drop_duplicates(subset="id", keep="first")

    # Parse genres from Python-literal JSON
    print("  Parsing genres...")
    df["genres"] = df["genres"].apply(lambda x: _extract_names(_safe_literal_eval(x)))

    # Parse release_date
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")

    # Ensure numeric columns
    for col in ["vote_average", "vote_count", "popularity"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["vote_count"] = df["vote_count"].astype(int)

    # Select and rename columns
    result = df[
        ["id", "imdb_id", "title", "overview", "genres", "release_date",
         "vote_average", "vote_count", "popularity", "poster_path"]
    ].copy()
    result = result.rename(columns={"id": "tmdb_id"})

    print(f"  Loaded {len(result)} movies from TMDb metadata.")
    return result


def load_keywords(tmdb_dir: Path) -> pd.DataFrame:
    """Load and parse TMDb keywords.csv."""
    print("Loading keywords.csv...")
    df = pd.read_csv(tmdb_dir / "keywords.csv")
    df["id"] = pd.to_numeric(df["id"], errors="coerce").dropna().astype(int)
    df["keywords"] = df["keywords"].apply(lambda x: _extract_names(_safe_literal_eval(x)))
    result = df[["id", "keywords"]].rename(columns={"id": "tmdb_id"})
    print(f"  Loaded keywords for {len(result)} movies.")
    return result


def load_credits(tmdb_dir: Path) -> pd.DataFrame:
    """Load and parse TMDb credits.csv (top 5 cast + director)."""
    print("Loading credits.csv...")
    df = pd.read_csv(tmdb_dir / "credits.csv")
    df["id"] = pd.to_numeric(df["id"], errors="coerce").dropna().astype(int)

    print("  Extracting cast and directors...")
    df["cast_names"] = df["cast"].apply(_extract_top_cast)
    df["director"] = df["crew"].apply(_extract_director)

    result = df[["id", "cast_names", "director"]].rename(columns={"id": "tmdb_id"})
    print(f"  Loaded credits for {len(result)} movies.")
    return result


def load_movielens_links(ml_dir: Path) -> pd.DataFrame:
    """Load MovieLens links.csv (movieId <-> tmdbId mapping)."""
    print("Loading links.csv...")
    df = pd.read_csv(ml_dir / "links.csv")
    df["tmdbId"] = pd.to_numeric(df["tmdbId"], errors="coerce")
    df = df.dropna(subset=["tmdbId"])
    df["tmdbId"] = df["tmdbId"].astype(int)
    df = df.rename(columns={"movieId": "movielens_id", "tmdbId": "tmdb_id", "imdbId": "imdb_id_ml"})
    print(f"  Loaded {len(df)} movie links.")
    return df


def load_ratings(ml_dir: Path) -> pd.DataFrame:
    """Load MovieLens ratings.csv."""
    print("Loading ratings.csv (~25M rows, this may take a moment)...")
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

    ml_dir = raw_dir / "ml-25m"
    tmdb_dir = raw_dir / "tmdb"

    # Validate input files exist
    for path, name in [(ml_dir / "ratings.csv", "MovieLens ratings"),
                       (ml_dir / "links.csv", "MovieLens links"),
                       (tmdb_dir / "movies_metadata.csv", "TMDb metadata")]:
        if not path.exists():
            raise FileNotFoundError(f"{name} not found at {path}. Run download_data.py first.")

    # --- Load all sources ---
    metadata = load_tmdb_metadata(tmdb_dir)
    keywords = load_keywords(tmdb_dir)
    credits = load_credits(tmdb_dir)
    links = load_movielens_links(ml_dir)
    ratings = load_ratings(ml_dir)

    # --- Join TMDb tables ---
    print("\nJoining TMDb metadata + keywords + credits...")
    movies = metadata.merge(keywords, on="tmdb_id", how="left")
    movies = movies.merge(credits, on="tmdb_id", how="left")

    # Fill NaN lists with empty lists
    for col in ["keywords", "cast_names"]:
        movies[col] = movies[col].apply(lambda x: x if isinstance(x, list) else [])

    # --- Join with MovieLens links ---
    print("Joining with MovieLens links...")
    movies = movies.merge(links[["movielens_id", "tmdb_id"]], on="tmdb_id", how="inner")
    print(f"  Movies with MovieLens IDs: {len(movies)}")

    # --- Filter: drop movies without overview ---
    before = len(movies)
    movies = movies.dropna(subset=["overview"])
    movies = movies[movies["overview"].str.strip().str.len() > 0]
    print(f"  Dropped {before - len(movies)} movies without overview. Remaining: {len(movies)}")

    # --- Filter: drop movies with < min_ratings ---
    rating_counts = ratings.groupby("movielens_id").size()
    popular_movies = set(rating_counts[rating_counts >= min_ratings_per_movie].index)
    before = len(movies)
    movies = movies[movies["movielens_id"].isin(popular_movies)]
    print(f"  Dropped {before - len(movies)} movies with <{min_ratings_per_movie} ratings. Remaining: {len(movies)}")

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
        ["movie_id", "tmdb_id", "imdb_id", "movielens_id", "title", "overview",
         "genres", "keywords", "cast_names", "director", "release_date",
         "vote_average", "vote_count", "popularity", "poster_path"]
    ]
    movies_out.to_parquet(processed_dir / "movies_clean.parquet", index=False)
    print(f"  movies_clean.parquet: {len(movies_out)} rows")

    ratings_out = ratings[["user_id", "movie_id", "rating", "timestamp"]].copy()
    ratings_out.to_parquet(processed_dir / "ratings_clean.parquet", index=False)
    print(f"  ratings_clean.parquet: {len(ratings_out):,} rows")

    id_mapping.to_parquet(processed_dir / "id_mapping.parquet", index=False)
    print(f"  id_mapping.parquet: {len(id_mapping)} rows")

    # Save user ID mapping for ALS
    user_mapping = pd.DataFrame(
        {"user_id": list(user_id_map.values()), "movielens_id": list(user_id_map.keys())}
    )
    user_mapping.to_parquet(processed_dir / "user_mapping.parquet", index=False)
    print(f"  user_mapping.parquet: {len(user_mapping)} rows")

    print("\n[OK] Cleaning complete.")
    return movies_out, ratings_out, id_mapping


if __name__ == "__main__":
    clean_and_join()
