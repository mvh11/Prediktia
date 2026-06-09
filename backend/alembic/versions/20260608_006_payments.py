"""Tabla payments para Webpay Plus."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260608_006"
down_revision = "20260608_005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("buy_order", sa.String(length=26), nullable=False),
        sa.Column("session_id", sa.String(length=61), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("buy_order"),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"], unique=False)
    op.create_index("ix_payments_status", "payments", ["status"], unique=False)
    op.create_index("ix_payments_buy_order", "payments", ["buy_order"], unique=True)
    op.create_index("ix_payments_token", "payments", ["token"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payments_token", table_name="payments")
    op.drop_index("ix_payments_buy_order", table_name="payments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_table("payments")
