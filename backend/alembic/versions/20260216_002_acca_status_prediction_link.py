"""acca_history.status (pending/won/lost) y predictions.acca_id para enlazar picks a una ACCA."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260216_002"
down_revision = "20260215_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "acca_history",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
    )
    op.execute(
        """
        UPDATE acca_history
        SET status = CASE
            WHEN lower(coalesce(result, '')) IN ('won', 'ganada', 'win') THEN 'won'
            WHEN lower(coalesce(result, '')) IN ('lost', 'perdida', 'loss') THEN 'lost'
            ELSE 'pending'
        END
        """
    )
    op.add_column("predictions", sa.Column("acca_id", sa.String(length=36), nullable=True))
    op.create_index("ix_predictions_acca_id", "predictions", ["acca_id"], unique=False)
    op.create_foreign_key(
        "fk_predictions_acca_history_acca_id",
        "predictions",
        "acca_history",
        ["acca_id"],
        ["acca_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_predictions_acca_history_acca_id", "predictions", type_="foreignkey")
    op.drop_index("ix_predictions_acca_id", table_name="predictions")
    op.drop_column("predictions", "acca_id")
    op.drop_column("acca_history", "status")
