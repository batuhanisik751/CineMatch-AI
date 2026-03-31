"""Add GIN index on movies.keywords for efficient JSONB containment queries.

This enables fast @> (contains) queries used by the Keyword/Tag Cloud Explorer feature.
Non-destructive additive migration — safe to run at any time.

Revision ID: 005_gin_index_keywords
Revises: 004_gin_index_cast_names
Create Date: 2026-03-30

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "005_gin_index_keywords"
down_revision: str | None = "004_gin_index_cast_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "idx_movies_keywords",
        "movies",
        ["keywords"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_movies_keywords", table_name="movies")
