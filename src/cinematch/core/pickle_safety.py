"""SHA-256 checksum verification for pickle artifacts."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from cinematch.config import get_settings

logger = logging.getLogger(__name__)

VerificationStatus = Literal[
    "verified", "mismatch", "missing_checksum", "missing_artifact"
]

_CHUNK_SIZE = 65_536  # 64 KB


def compute_sha256(file_path: str | Path) -> str:
    """Compute SHA-256 hex digest of a file, reading in 64KB chunks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(_CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def save_checksum(artifact_path: str | Path) -> Path:
    """Compute and write a .sha256 sidecar file next to the artifact.

    The sidecar contains: ``<hex_digest>  <filename>\\n``
    (two-space separator, matching ``shasum`` format).
    """
    artifact_path = Path(artifact_path)
    digest = compute_sha256(artifact_path)
    sidecar = artifact_path.with_suffix(artifact_path.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {artifact_path.name}\n")
    return sidecar


def read_expected_checksum(artifact_path: str | Path) -> str | None:
    """Read the expected checksum from the .sha256 sidecar file.

    Returns ``None`` if the sidecar does not exist.
    """
    sidecar = Path(artifact_path).with_suffix(
        Path(artifact_path).suffix + ".sha256"
    )
    if not sidecar.exists():
        return None
    content = sidecar.read_text().strip()
    # shasum format: "<hash>  <filename>" — take only the hash part
    return content.split()[0] if content else None


def verify_checksum(artifact_path: str | Path) -> VerificationStatus:
    """Verify a pickle artifact against its .sha256 sidecar."""
    artifact_path = Path(artifact_path)
    if not artifact_path.exists():
        return "missing_artifact"

    expected = read_expected_checksum(artifact_path)
    if expected is None:
        return "missing_checksum"

    actual = compute_sha256(artifact_path)
    return "verified" if actual == expected else "mismatch"


def verify_and_log(artifact_path: str | Path) -> VerificationStatus:
    """Verify checksum and log at the appropriate level."""
    status = verify_checksum(artifact_path)
    name = Path(artifact_path).name

    if status == "verified":
        logger.info("Checksum verified for %s", name)
    elif status == "mismatch":
        logger.error(
            "CHECKSUM MISMATCH for %s — file may have been tampered with!",
            name,
        )
    elif status == "missing_checksum":
        logger.warning(
            "No .sha256 sidecar for %s — skipping integrity check", name
        )
    elif status == "missing_artifact":
        logger.warning("Artifact not found: %s", name)

    return status


def get_all_artifact_statuses() -> list[dict]:
    """Check all configured pickle artifacts and return their integrity info."""
    settings = get_settings()
    paths = [
        settings.faiss_id_map_path,
        settings.als_model_path,
        settings.als_user_map_path,
        settings.als_item_map_path,
    ]

    results: list[dict] = []
    for path_str in paths:
        p = Path(path_str)
        status = verify_checksum(p)
        expected = read_expected_checksum(p)
        actual = compute_sha256(p) if p.exists() else None

        file_size: int | None = None
        last_modified: datetime | None = None
        if p.exists():
            stat = p.stat()
            file_size = stat.st_size
            last_modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)

        results.append(
            {
                "file_name": p.name,
                "file_path": str(p),
                "expected_hash": expected,
                "actual_hash": actual,
                "status": status,
                "file_size_bytes": file_size,
                "last_modified": last_modified,
            }
        )

    return results
