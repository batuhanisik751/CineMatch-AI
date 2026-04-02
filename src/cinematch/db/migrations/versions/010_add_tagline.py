"""Add tagline column to movies table.

Revision ID: 010_add_tagline
Revises: 009_add_runtime
Create Date: 2026-04-02

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010_add_tagline"
down_revision: str | None = "009_add_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("tagline", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "tagline")
