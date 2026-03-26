"""Download all datasets for CineMatch-AI."""

from cinematch.pipeline.downloader import check_tmdb, download_movielens


def main() -> None:
    print("=== CineMatch-AI Data Download ===\n")

    # Step 1: MovieLens (automatic)
    download_movielens()
    print()

    # Step 2: TMDb metadata (manual)
    tmdb_dir = check_tmdb()
    if tmdb_dir is None:
        print("\nPlease download TMDb data and re-run this script to verify.")
    else:
        print("\nAll datasets ready! Run: python scripts/train_models.py")


if __name__ == "__main__":
    main()
