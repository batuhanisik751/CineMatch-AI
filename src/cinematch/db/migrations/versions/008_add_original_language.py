"""Add original_language column to movies table.

Revision ID: 008_add_original_language
Revises: 007_add_user_lists
Create Date: 2026-04-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008_add_original_language"
down_revision: str | None = "007_add_user_lists"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("original_language", sa.String(10), nullable=True))
    op.create_index("idx_movies_original_language", "movies", ["original_language"])


def downgrade() -> None:
    op.drop_index("idx_movies_original_language", table_name="movies")
    op.drop_column("movies", "original_language")
