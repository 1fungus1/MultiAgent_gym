"""Add appointment action audit log.

Revision ID: 20261107_0002
Revises: 20261102_0001
Create Date: 2026-11-07
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261107_0002"
down_revision: str | None = "20261102_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "appointment_action_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("appointment_id", sa.BigInteger(), nullable=False),
        sa.Column("member_id", sa.BigInteger(), nullable=False),
        sa.Column("course_id", sa.BigInteger(), nullable=False),
        sa.Column("target_course_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("detail", sa.String(length=255), nullable=True),
        sa.Column(
            "create_time",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_appointment_log_create_time",
        "appointment_action_log",
        ["create_time"],
    )
    op.create_index(
        "idx_appointment_log_member",
        "appointment_action_log",
        ["member_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_appointment_log_member",
        table_name="appointment_action_log",
    )
    op.drop_index(
        "idx_appointment_log_create_time",
        table_name="appointment_action_log",
    )
    op.drop_table("appointment_action_log")

