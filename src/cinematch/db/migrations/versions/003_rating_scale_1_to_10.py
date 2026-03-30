"""Change rating scale from 0.5-5.0 (float) to 1-10 (integer).

WARNING: ALTER COLUMN with type cast triggers a full table rewrite and exclusive lock
on `ratings`. On ml-25m (~25M rows) this may take several minutes. Run during a
maintenance window or when the application is offline.

WARNING: The downgrade is NOT a lossless round-trip. Any integer ratings created after
the upgrade (e.g. a user rates 7/10) will downgrade to 3.5, which may not match the
original user intent. Treat this as a one-way migration once new ratings are collected.

Pre-flight check before running:
    SELECT COUNT(*) FROM ratings WHERE rating < 0.5 OR rating > 5.0;
This should return 0. If not, fix out-of-range rows first.

Revision ID: 003_rating_scale_1_to_10
Revises: 002_add_watchlist
Create Date: 2026-03-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_rating_scale_1_to_10"
down_revision: str | None = "002_add_watchlist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Drop old CHECK constraint
    op.drop_constraint("ck_rating_range", "ratings", type_="check")

    # 2. Scale existing ratings: multiply by 2 and round to integer
    op.execute("UPDATE ratings SET rating = ROUND(rating * 2)")

    # 3. Change column type from Float to Integer
    op.alter_column(
        "ratings",
        "rating",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="rating::integer",
    )

    # 4. Add new CHECK constraint for 1-10 range
    op.create_check_constraint("ck_rating_range", "ratings", "rating >= 1 AND rating <= 10")


def downgrade() -> None:
    # 1. Drop new CHECK constraint
    op.drop_constraint("ck_rating_range", "ratings", type_="check")

    # 2. Change column type back to Float
    op.alter_column(
        "ratings",
        "rating",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using="rating::double precision",
    )

    # 3. Scale ratings back: divide by 2
    op.execute("UPDATE ratings SET rating = rating / 2.0")

    # 4. Restore old CHECK constraint
    op.create_check_constraint("ck_rating_range", "ratings", "rating >= 0.5 AND rating <= 5.0")
