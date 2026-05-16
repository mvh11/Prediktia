"""Tablas analíticas iniciales: fixtures, teams, odds, predictions, acca_history, model_metrics."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260215_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fixtures",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=True),
        sa.Column("league", sa.String(length=512), nullable=False),
        sa.Column("home_team", sa.String(length=255), nullable=False),
        sa.Column("away_team", sa.String(length=255), nullable=False),
        sa.Column("kickoff", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fixture_id"),
    )
    op.create_index("ix_fixtures_league_id", "fixtures", ["league_id"], unique=False)

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )

    op.create_table(
        "odds_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("bookmaker", sa.String(length=128), nullable=False),
        sa.Column("market", sa.String(length=128), nullable=False),
        sa.Column("selection", sa.String(length=256), nullable=False),
        sa.Column("odd", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_odds_snapshots_fixture_id", "odds_snapshots", ["fixture_id"], unique=False)

    op.create_table(
        "predictions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("market", sa.String(length=128), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("implied_probability", sa.Float(), nullable=False),
        sa.Column("ev", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_fixture_id", "predictions", ["fixture_id"], unique=False)

    op.create_table(
        "acca_history",
        sa.Column("acca_id", sa.String(length=36), nullable=False),
        sa.Column("risk_profile", sa.String(length=32), nullable=False),
        sa.Column("fixture_date", sa.Date(), nullable=True),
        sa.Column("total_odds", sa.Float(), nullable=False),
        sa.Column("combined_ev", sa.Float(), nullable=False),
        sa.Column("combined_ev_pct", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("volatility_score", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("picks_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=True),
        sa.Column("roi", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("acca_id"),
    )
    op.create_index("ix_acca_history_risk_profile", "acca_history", ["risk_profile"], unique=False)
    op.create_index("ix_acca_history_fixture_date", "acca_history", ["fixture_date"], unique=False)
    op.create_index("ix_acca_history_created_at", "acca_history", ["created_at"], unique=False)

    op.create_table(
        "model_metrics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=128), nullable=True),
        sa.Column("value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_metrics_name", "model_metrics", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_model_metrics_name", table_name="model_metrics")
    op.drop_table("model_metrics")
    op.drop_index("ix_acca_history_created_at", table_name="acca_history")
    op.drop_index("ix_acca_history_fixture_date", table_name="acca_history")
    op.drop_index("ix_acca_history_risk_profile", table_name="acca_history")
    op.drop_table("acca_history")
    op.drop_index("ix_predictions_fixture_id", table_name="predictions")
    op.drop_table("predictions")
    op.drop_index("ix_odds_snapshots_fixture_id", table_name="odds_snapshots")
    op.drop_table("odds_snapshots")
    op.drop_table("teams")
    op.drop_index("ix_fixtures_league_id", table_name="fixtures")
    op.drop_table("fixtures")
