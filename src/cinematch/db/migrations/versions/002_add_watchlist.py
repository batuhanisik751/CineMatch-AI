"""Add watchlist table.

Revision ID: 002_add_watchlist
Revises: 001_initial
Create Date: 2026-03-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_add_watchlist"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "movie_id",
            sa.Integer(),
            sa.ForeignKey("movies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "movie_id", name="uq_watchlist_user_movie"),
    )

    op.create_index("idx_watchlist_user_id", "watchlist", ["user_id"])
    op.create_index("idx_watchlist_movie_id", "watchlist", ["movie_id"])
    op.create_index("idx_watchlist_added_at", "watchlist", ["added_at"])


def downgrade() -> None:
    op.drop_table("watchlist")
