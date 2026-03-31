"""Add dismissals table for 'Not Interested' feedback.

Revision ID: 006_add_dismissals
Revises: 005_gin_index_keywords
Create Date: 2026-03-31

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006_add_dismissals"
down_revision: str | None = "005_gin_index_keywords"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dismissals",
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
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "movie_id", name="uq_dismissal_user_movie"),
    )

    op.create_index("idx_dismissals_user_id", "dismissals", ["user_id"])
    op.create_index("idx_dismissals_movie_id", "dismissals", ["movie_id"])
    op.create_index("idx_dismissals_dismissed_at", "dismissals", ["dismissed_at"])


def downgrade() -> None:
    op.drop_table("dismissals")
