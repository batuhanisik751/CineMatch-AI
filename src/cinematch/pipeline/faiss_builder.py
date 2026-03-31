"""Build FAISS index from movie embeddings."""

from __future__ import annotations

import pickle
from pathlib import Path

import faiss
import numpy as np
import pandas as pd

from cinematch.config import get_settings


def build_faiss_index(
    processed_dir: str | None = None,
    index_path: str | None = None,
    id_map_path: str | None = None,
) -> None:
    """Build a FAISS IndexFlatIP from embeddings and save it."""
    settings = get_settings()
    processed_dir = Path(processed_dir or settings.data_processed_dir)
    index_path = Path(index_path or settings.faiss_index_path)
    id_map_path = Path(id_map_path or settings.faiss_id_map_path)

    # Load embeddings
    embeddings_path = processed_dir / "embeddings.npy"
    if not embeddings_path.exists():
        raise FileNotFoundError(
            f"embeddings.npy not found at {embeddings_path}. Run embedder first."
        )

    print(f"Loading embeddings from {embeddings_path}...")
    embeddings = np.load(embeddings_path).astype(np.float32)
    print(f"  Shape: {embeddings.shape}")

    # Load movie IDs (ordered, matching embedding rows)
    movies_path = processed_dir / "movies_clean.parquet"
    movies = pd.read_parquet(movies_path, columns=["movie_id"])
    movie_ids = movies["movie_id"].tolist()

    if len(movie_ids) != embeddings.shape[0]:
        raise ValueError(
            f"Mismatch: {len(movie_ids)} movie IDs vs {embeddings.shape[0]} embeddings"
        )

    # Build index
    dimension = embeddings.shape[1]
    print(f"Building FAISS IndexFlatIP (dim={dimension})...")
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    print(f"  Index size: {index.ntotal} vectors")

    # Save index
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    print(f"  Saved index to {index_path}")

    # Save ID map
    with open(id_map_path, "wb") as f:
        pickle.dump(movie_ids, f)
    print(f"  Saved ID map to {id_map_path} ({len(movie_ids)} entries)")

    # Quick sanity check: query first movie against itself
    distances, indices = index.search(embeddings[:1], 5)
    print(f"  Sanity check — top 5 for first movie: distances={distances[0].tolist()}")

    print("[OK] FAISS index built.")


if __name__ == "__main__":
    build_faiss_index()
