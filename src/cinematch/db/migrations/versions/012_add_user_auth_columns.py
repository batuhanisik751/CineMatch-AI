"""Add authentication columns to users table.

Revision ID: 012_add_user_auth_columns
Revises: 011_add_budget_revenue
Create Date: 2026-04-03

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012_add_user_auth_columns"
down_revision: str | None = "011_add_budget_revenue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(320), nullable=True))
    op.add_column("users", sa.Column("hashed_password", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("username", sa.String(50), nullable=True))

    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # Allow registered users to have no movielens_id
    op.alter_column("users", "movielens_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "movielens_id", existing_type=sa.Integer(), nullable=False)

    op.drop_index("ix_users_username", table_name="users")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_constraint("uq_users_email", "users", type_="unique")

    op.drop_column("users", "username")
    op.drop_column("users", "hashed_password")
    op.drop_column("users", "email")
