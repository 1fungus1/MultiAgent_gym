"""Add notification center.

Revision ID: 20261107_0003
Revises: 20261107_0002
Create Date: 2026-11-07
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261107_0003"
down_revision: str | None = "20261107_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("member_id", sa.BigInteger(), nullable=True),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("content", sa.String(length=500), nullable=False),
        sa.Column("related_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "create_time",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_notification_user_read",
        "notification",
        ["user_id", "is_read"],
    )
    op.create_index(
        "idx_notification_create_time",
        "notification",
        ["create_time"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_notification_create_time",
        table_name="notification",
    )
    op.drop_index(
        "idx_notification_user_read",
        table_name="notification",
    )
    op.drop_table("notification")

