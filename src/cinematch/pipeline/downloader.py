"""Download datasets for the CineMatch-AI pipeline."""

from __future__ import annotations

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
    """Download and extract MovieLens ml-32m dataset.

    Returns the path to the extracted directory.
    """
    settings = get_settings()
    raw_dir = Path(raw_dir or settings.data_raw_dir)
    ml_dir = raw_dir / "ml-32m"
    zip_path = raw_dir / "ml-32m.zip"
    url = "https://files.grouplens.org/datasets/movielens/ml-32m.zip"

    # Check if already extracted
    required_files = ["ratings.csv", "movies.csv", "links.csv", "tags.csv"]
    if all((ml_dir / f).exists() for f in required_files):
        print(f"[OK] MovieLens ml-32m already exists at {ml_dir}")
        return ml_dir

    raw_dir.mkdir(parents=True, exist_ok=True)

    # Download
    if not zip_path.exists():
        print("Downloading MovieLens ml-32m (~440MB)...")
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
    print("[OK] MovieLens ml-32m ready.")
    return ml_dir


def check_tmdb(raw_dir: str | None = None) -> Path | None:
    """Check if TMDb metadata file exists. Print instructions if missing.

    Returns the path to TMDB_all_movies.csv if it exists, None otherwise.
    """
    settings = get_settings()
    raw_dir = Path(raw_dir or settings.data_raw_dir)
    tmdb_path = raw_dir / "TMDB_all_movies.csv"

    if tmdb_path.exists():
        print(f"[OK] TMDb metadata found at {tmdb_path}")
        return tmdb_path

    print("\n" + "=" * 70)
    print("TMDb metadata NOT found. Please download manually:")
    print("=" * 70)
    print()
    print("Option 1: Download from Kaggle website")
    print("  1. Visit: https://www.kaggle.com/datasets/alanvourch/tmdb-movies-daily-updates")
    print("  2. Download the dataset")
    print(f"  3. Place TMDB_all_movies.csv in {raw_dir}/")
    print()
    print("Option 2: Use Kaggle CLI")
    print("  kaggle datasets download -d alanvourch/tmdb-movies-daily-updates")
    print(f"  unzip tmdb-movies-daily-updates.zip -d {raw_dir}/")
    print()
    print("=" * 70)
    return None


if __name__ == "__main__":
    download_movielens()
    check_tmdb()
