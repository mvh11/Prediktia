"""Modelos analíticos: fixtures, cuotas, predicciones, historial ACCA, métricas."""

from __future__ import annotations

from datetime import date as date_py
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FixtureRow(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    league_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    league: Mapped[str] = mapped_column(String(512), default="")
    home_team: Mapped[str] = mapped_column(String(255), default="")
    away_team: Mapped[str] = mapped_column(String(255), default="")
    kickoff: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scores: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TeamRow(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OddsSnapshotRow(Base):
    __tablename__ = "odds_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    bookmaker: Mapped[str] = mapped_column(String(128), default="")
    market: Mapped[str] = mapped_column(String(128), default="")
    selection: Mapped[str] = mapped_column(String(256), default="")
    odd: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PredictionRow(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    acca_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("acca_history.acca_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fixture_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    market: Mapped[str] = mapped_column(String(128), default="")
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    implied_probability: Mapped[float] = mapped_column(Float, nullable=False)
    ev: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AccaHistoryRow(Base):
    __tablename__ = "acca_history"

    acca_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    risk_profile: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    fixture_date: Mapped[date_py | None] = mapped_column(Date, nullable=True, index=True)
    total_odds: Mapped[float] = mapped_column(Float, nullable=False)
    combined_ev: Mapped[float] = mapped_column(Float, nullable=False)
    combined_ev_pct: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), default="")
    picks_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    roi: Mapped[float | None] = mapped_column(Float, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ModelMetricRow(Base):
    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scope: Mapped[str | None] = mapped_column(String(128), nullable=True)
    value_json: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    period_start: Mapped[date_py | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date_py | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
