"""Add budget and revenue columns to movies table.

Revision ID: 011_add_budget_revenue
Revises: 010_add_tagline
Create Date: 2026-04-02

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011_add_budget_revenue"
down_revision: str | None = "010_add_tagline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("budget", sa.BigInteger(), nullable=True))
    op.add_column("movies", sa.Column("revenue", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "revenue")
    op.drop_column("movies", "budget")
