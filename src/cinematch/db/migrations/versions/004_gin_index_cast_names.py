"""Add GIN index on movies.cast_names for efficient JSONB containment queries.

This enables fast @> (contains) queries used by the Actor Filmography feature.
Non-destructive additive migration — safe to run at any time.

Revision ID: 004_gin_index_cast_names
Revises: 003_rating_scale_1_to_10
Create Date: 2026-03-30

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "004_gin_index_cast_names"
down_revision: str | None = "003_rating_scale_1_to_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "idx_movies_cast_names",
        "movies",
        ["cast_names"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_movies_cast_names", table_name="movies")
