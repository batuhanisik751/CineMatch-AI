"""Generate movie embeddings using sentence-transformers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from cinematch.config import get_settings


def build_movie_text(row: pd.Series) -> str:
    """Construct the text representation of a movie for embedding."""
    parts = [f"{row['title']}."]
    if pd.notna(row.get("overview")) and row["overview"]:
        parts.append(str(row["overview"]))
    genres = row.get("genres", [])
    if isinstance(genres, list) and genres:
        parts.append(f"Genres: {', '.join(genres)}.")
    keywords = row.get("keywords", [])
    if isinstance(keywords, list) and keywords:
        parts.append(f"Keywords: {', '.join(keywords)}.")
    return " ".join(parts)


def generate_embeddings(
    processed_dir: str | None = None,
    model_name: str | None = None,
    batch_size: int | None = None,
) -> np.ndarray:
    """Generate embeddings for all movies in movies_clean.parquet.

    Returns the embeddings array (N, 384).
    """
    settings = get_settings()
    processed_dir = Path(processed_dir or settings.data_processed_dir)
    model_name = model_name or settings.embedding_model_name
    batch_size = batch_size or settings.embedding_batch_size

    # Load movies
    movies_path = processed_dir / "movies_clean.parquet"
    if not movies_path.exists():
        raise FileNotFoundError(f"movies_clean.parquet not found at {movies_path}. Run cleaner first.")

    print(f"Loading movies from {movies_path}...")
    movies = pd.read_parquet(movies_path)
    print(f"  {len(movies)} movies loaded.")

    # Build text representations
    print("Building text representations...")
    texts = [build_movie_text(row) for _, row in movies.iterrows()]
    print(f"  Average text length: {np.mean([len(t) for t in texts]):.0f} characters")

    # Load model
    print(f"Loading embedding model: {model_name}...")
    model = SentenceTransformer(model_name)

    # Generate embeddings
    print(f"Generating embeddings (batch_size={batch_size})...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,  # L2-normalize: cosine similarity = dot product
    )

    # Save
    output_path = processed_dir / "embeddings.npy"
    np.save(output_path, embeddings)
    print(f"  Saved embeddings: shape={embeddings.shape}, dtype={embeddings.dtype}")
    print(f"  File: {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print("[OK] Embedding generation complete.")

    return embeddings


if __name__ == "__main__":
    generate_embeddings()
