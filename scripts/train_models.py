"""Orchestrate the full data pipeline: clean -> embed -> FAISS -> ALS."""

from __future__ import annotations

import time


def main() -> None:
    print("=" * 60)
    print("CineMatch-AI — Full Data Pipeline")
    print("=" * 60)

    total_start = time.time()

    # Step 1: Clean and join datasets
    print("\n[1/4] Cleaning and joining datasets...")
    step_start = time.time()
    from cinematch.pipeline.cleaner import clean_and_join
    clean_and_join()
    print(f"  Time: {time.time() - step_start:.1f}s")

    # Step 2: Generate embeddings
    print("\n[2/4] Generating embeddings...")
    step_start = time.time()
    from cinematch.pipeline.embedder import generate_embeddings
    generate_embeddings()
    print(f"  Time: {time.time() - step_start:.1f}s")

    # Step 3: Build FAISS index
    print("\n[3/4] Building FAISS index...")
    step_start = time.time()
    from cinematch.pipeline.faiss_builder import build_faiss_index
    build_faiss_index()
    print(f"  Time: {time.time() - step_start:.1f}s")

    # Step 4: Train ALS model
    print("\n[4/4] Training ALS collaborative filtering model...")
    step_start = time.time()
    from cinematch.pipeline.collaborative import train_als
    train_als()
    print(f"  Time: {time.time() - step_start:.1f}s")

    total_time = time.time() - total_start
    print("\n" + "=" * 60)
    print(f"Pipeline complete! Total time: {total_time:.1f}s ({total_time / 60:.1f}m)")
    print("=" * 60)
    print("\nNext step: python scripts/seed_db.py")


if __name__ == "__main__":
    main()
