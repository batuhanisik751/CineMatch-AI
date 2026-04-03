"""Shared test fixtures."""

import os

# Set env var defaults BEFORE any cinematch imports.
# Required because config.py fields are now SecretStr with no defaults,
# and session.py calls get_settings() at module import time.
os.environ.setdefault(
    "CINEMATCH_DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test",
)
os.environ.setdefault(
    "CINEMATCH_DATABASE_URL_SYNC",
    "postgresql://test:test@localhost:5432/test",
)
os.environ.setdefault("CINEMATCH_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CINEMATCH_SECRET_KEY", "test-secret-key-not-for-production")
