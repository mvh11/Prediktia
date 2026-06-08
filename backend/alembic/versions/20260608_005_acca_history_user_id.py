"""acca_history.user_id para historial por usuario."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260608_005"
down_revision = "20260608_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("acca_history", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_acca_history_user_id_users",
        "acca_history",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_acca_history_user_id", "acca_history", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_acca_history_user_id", table_name="acca_history")
    op.drop_constraint("fk_acca_history_user_id_users", "acca_history", type_="foreignkey")
    op.drop_column("acca_history", "user_id")
