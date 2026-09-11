"""initial schema: users, fdc_foods, food_log

Revision ID: 0001_initial_schema
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # gen_random_uuid() lives in pgcrypto (core in PG13+, but the extension
    # guarantees availability across images).
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "fdc_foods",
        sa.Column("fdc_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("food_name", sa.String(length=500), nullable=False),
        sa.Column(
            "energy_kcal_per_100g", sa.Numeric(precision=8, scale=2), nullable=True
        ),
        sa.Column(
            "protein_g_per_100g", sa.Numeric(precision=8, scale=2), nullable=True
        ),
        sa.Column("fat_g_per_100g", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("carbs_g_per_100g", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column(
            "cached_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("fdc_id", name="pk_fdc_foods"),
    )

    op.create_table(
        "food_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fdc_id", sa.Integer(), nullable=False),
        sa.Column("food_name", sa.String(length=500), nullable=False),
        sa.Column("portion_grams", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("calories_kcal", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("protein_g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("fat_g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("carbs_g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("eaten_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_food_log"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_food_log_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fdc_id"],
            ["fdc_foods.fdc_id"],
            name="fk_food_log_fdc_id_fdc_foods",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_food_log_fdc_id", "food_log", ["fdc_id"], unique=False)
    op.create_index(
        "ix_food_log_user_id_eaten_at",
        "food_log",
        ["user_id", "eaten_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_food_log_user_id_eaten_at", table_name="food_log")
    op.drop_index("ix_food_log_fdc_id", table_name="food_log")
    op.drop_table("food_log")
    op.drop_table("fdc_foods")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
