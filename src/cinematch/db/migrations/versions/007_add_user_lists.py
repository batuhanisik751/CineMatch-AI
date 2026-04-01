"""Add user_lists and user_list_items tables for custom movie collections.

Revision ID: 007_add_user_lists
Revises: 006_add_dismissals
Create Date: 2026-03-31

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_add_user_lists"
down_revision: str | None = "006_add_dismissals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- user_lists table ---
    op.create_table(
        "user_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_user_list_name"),
    )

    op.create_index("idx_user_lists_user_id", "user_lists", ["user_id"])
    op.create_index("idx_user_lists_is_public", "user_lists", ["is_public"])
    op.create_index("idx_user_lists_created_at", "user_lists", ["created_at"])

    # --- user_list_items table ---
    op.create_table(
        "user_list_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "list_id",
            sa.Integer(),
            sa.ForeignKey("user_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "movie_id",
            sa.Integer(),
            sa.ForeignKey("movies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("list_id", "movie_id", name="uq_list_item_list_movie"),
    )

    op.create_index("idx_user_list_items_list_id", "user_list_items", ["list_id"])
    op.create_index("idx_user_list_items_movie_id", "user_list_items", ["movie_id"])


def downgrade() -> None:
    op.drop_table("user_list_items")
    op.drop_table("user_lists")
