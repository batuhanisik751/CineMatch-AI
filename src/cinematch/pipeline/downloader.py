"""Download datasets for the CineMatch-AI pipeline."""

from __future__ import annotations

import os
import sys
import urllib.request
import zipfile
from pathlib import Path

from cinematch.config import get_settings


def _progress_hook(block_num: int, block_size: int, total_size: int) -> None:
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(100, downloaded * 100 // total_size)
        mb = downloaded / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        sys.stdout.write(f"\r  Downloading: {mb:.1f}/{total_mb:.1f} MB ({pct}%)")
        sys.stdout.flush()


def download_movielens(raw_dir: str | None = None) -> Path:
    """Download and extract MovieLens ml-25m dataset.

    Returns the path to the extracted directory.
    """
    settings = get_settings()
    raw_dir = Path(raw_dir or settings.data_raw_dir)
    ml_dir = raw_dir / "ml-25m"
    zip_path = raw_dir / "ml-25m.zip"
    url = "https://files.grouplens.org/datasets/movielens/ml-25m.zip"

    # Check if already extracted
    required_files = ["ratings.csv", "movies.csv", "links.csv"]
    if all((ml_dir / f).exists() for f in required_files):
        print(f"[OK] MovieLens ml-25m already exists at {ml_dir}")
        return ml_dir

    raw_dir.mkdir(parents=True, exist_ok=True)

    # Download
    if not zip_path.exists():
        print(f"Downloading MovieLens ml-25m (~250MB)...")
        urllib.request.urlretrieve(url, zip_path, reporthook=_progress_hook)
        print("\n  Download complete.")
    else:
        print(f"[OK] Zip already downloaded at {zip_path}")

    # Extract
    print("Extracting...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(raw_dir)
    print(f"  Extracted to {ml_dir}")

    # Verify
    missing = [f for f in required_files if not (ml_dir / f).exists()]
    if missing:
        raise FileNotFoundError(f"Missing files after extraction: {missing}")

    # Clean up zip
    zip_path.unlink()
    print("[OK] MovieLens ml-25m ready.")
    return ml_dir


def check_tmdb(raw_dir: str | None = None) -> Path | None:
    """Check if TMDb metadata files exist. Print instructions if missing.

    Returns the tmdb directory path if all files exist, None otherwise.
    """
    settings = get_settings()
    raw_dir = Path(raw_dir or settings.data_raw_dir)
    tmdb_dir = raw_dir / "tmdb"

    required_files = ["movies_metadata.csv", "keywords.csv", "credits.csv"]
    missing = [f for f in required_files if not (tmdb_dir / f).exists()]

    if not missing:
        print(f"[OK] TMDb metadata found at {tmdb_dir}")
        return tmdb_dir

    print("\n" + "=" * 70)
    print("TMDb metadata NOT found. Please download manually:")
    print("=" * 70)
    print()
    print("Option 1: Download from Kaggle website")
    print("  1. Visit: https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset")
    print("  2. Download the dataset")
    print(f"  3. Place these files in {tmdb_dir}/")
    for f in required_files:
        status = "MISSING" if f in missing else "OK"
        print(f"     - {f} [{status}]")
    print()
    print("Option 2: Use Kaggle CLI")
    print("  kaggle datasets download -d rounakbanik/the-movies-dataset")
    print(f"  unzip the-movies-dataset.zip -d {tmdb_dir}/")
    print()
    print("=" * 70)
    return None


if __name__ == "__main__":
    download_movielens()
    check_tmdb()
