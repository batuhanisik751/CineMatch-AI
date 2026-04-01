"""Add runtime column to movies table.

Revision ID: 009_add_runtime
Revises: 008_add_original_language
Create Date: 2026-04-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009_add_runtime"
down_revision: str | None = "008_add_original_language"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("runtime", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "runtime")
