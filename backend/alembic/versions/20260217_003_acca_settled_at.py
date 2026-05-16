"""acca_history.settled_at para liquidación automática."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260217_003"
down_revision = "20260216_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "acca_history",
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_acca_history_settled_at", "acca_history", ["settled_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_acca_history_settled_at", table_name="acca_history")
    op.drop_column("acca_history", "settled_at")
