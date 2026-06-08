"""Implementación de persistencia ACCA (requiere SQLAlchemy + drivers instalados)."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import AccaHistoryRow, FixtureRow, PredictionRow
from app.db.session import session_scope

logger = logging.getLogger(__name__)

def _parse_kickoff_utc(raw: str | None) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _upsert_fixture_from_pick(db: Session, pick: dict[str, Any]) -> None:
    fid = int(pick["fixture_id"])
    kick = _parse_kickoff_utc(pick.get("fecha"))
    stmt = insert(FixtureRow).values(
        fixture_id=fid,
        league_id=None,
        league=(pick.get("liga") or "")[:512],
        home_team=(pick.get("equipo_local") or "")[:255],
        away_team=(pick.get("equipo_visitante") or "")[:255],
        kickoff=kick,
        status="NS",
        scores=None,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[FixtureRow.fixture_id],
        set_={
            "league": (pick.get("liga") or "")[:512],
            "home_team": (pick.get("equipo_local") or "")[:255],
            "away_team": (pick.get("equipo_visitante") or "")[:255],
            "kickoff": kick,
            "updated_at": func.now(),
        },
    )
    db.execute(stmt)


def persist_smart_acca(
    settings: Settings,
    result: dict[str, Any],
    *,
    user_id: int | None = None,
) -> tuple[str | None, str | None]:
    """
    Guarda historial ACCA, picks en `predictions` (con acca_id) y upsert de fixtures.

    Returns:
        (acca_id, None) si OK tras commit y verificación.
        (None, mensaje) si falló antes de persistir o el commit/insert falló.
        (acca_id, warning) si insert OK pero la lectura post-commit no encuentra la fila (anomalía).
    """
    if not settings.database_url:
        return None, "no_database_url"

    acca_id = str(uuid.uuid4())
    try:
        day = date.fromisoformat(str(result["date"]))
    except (ValueError, TypeError):
        day = None

    picks_in = [p for p in (result.get("picks") or []) if isinstance(p, dict)]
    if not picks_in:
        return None, "no_picks_to_persist"
    if user_id is None:
        return None, "login_required"

    logger.info(
        "PERSIST_ACCA_START acca_id=%s user_id=%s picks=%s risk=%s total_odds=%s",
        acca_id,
        user_id,
        len(picks_in),
        result.get("risk"),
        result.get("total_odds"),
    )
    try:
        with session_scope(settings.database_url) as db:
            if db is None:
                msg = "session_unavailable_engine_null"
                logger.error("PERSIST_ACCA_ERROR acca_id=%s reason=%s", acca_id, msg)
                return None, msg

            row = AccaHistoryRow(
                acca_id=acca_id,
                user_id=user_id,
                risk_profile=str(result.get("risk") or "medium"),
                fixture_date=day,
                total_odds=float(result.get("total_odds") or 0.0),
                combined_ev=float(result.get("combined_ev") or 0.0),
                combined_ev_pct=float(result.get("combined_ev_pct") or 0.0),
                confidence_score=float(result.get("confidence_score") or 0.0),
                risk_score=float(result["risk_score"]) if result.get("risk_score") is not None else None,
                volatility_score=float(result["volatility_score"])
                if result.get("volatility_score") is not None
                else None,
                model_version=str(result.get("model_version") or ""),
                picks_json=result.get("picks") or [],
                status="pending",
            )
            db.add(row)
            db.flush()
            logger.info(
                "PERSIST_ACCA_INSERT_HISTORY acca_id=%s fixture_date=%s picks_json_len=%s",
                acca_id,
                day,
                len(picks_in),
            )

            mv = str(result.get("model_version") or "")
            pred_count = 0
            for pick in picks_in:
                fid = pick.get("fixture_id")
                if fid is None:
                    continue
                mkt = f"{pick.get('mercado', '')}: {pick.get('pick', '')}".strip(": ").strip() or "unknown"
                if len(mkt) > 128:
                    mkt = mkt[:125] + "…"
                db.add(
                    PredictionRow(
                        acca_id=acca_id,
                        fixture_id=int(fid),
                        market=mkt,
                        probability=float(pick.get("probabilidad") or 0.0),
                        implied_probability=float(pick.get("implied_probability") or 0.0),
                        ev=float(pick.get("ev") or 0.0),
                        confidence=float(pick.get("confidence_pct") or 0.0),
                        model_version=mv,
                    )
                )
                pred_count += 1
            logger.info(
                "PERSIST_ACCA_INSERT_PREDICTIONS acca_id=%s prediction_rows=%s",
                acca_id,
                pred_count,
            )

            for pick in picks_in:
                if pick.get("fixture_id") is not None:
                    _upsert_fixture_from_pick(db, pick)

            row_in_txn = db.get(AccaHistoryRow, acca_id)
            logger.info(
                "PERSIST_ACCA_PRE_COMMIT_VERIFY acca_id=%s row_in_session=%s",
                acca_id,
                row_in_txn is not None,
            )

        logger.info("PERSIST_ACCA_COMMIT acca_id=%s (transaction committed)", acca_id)
    except Exception as exc:
        logger.exception(
            "PERSIST_ACCA_ERROR acca_id=%s traceback=logged type=%s msg=%s",
            acca_id,
            type(exc).__name__,
            exc,
        )
        return None, f"{type(exc).__name__}: {exc}"

    verify_warning: str | None = None
    try:
        with session_scope(settings.database_url) as db2:
            if db2 is None:
                verify_warning = "post_commit_verify_no_session"
                logger.error("PERSIST_ACCA_VERIFY_ERROR acca_id=%s %s", acca_id, verify_warning)
            else:
                row2 = db2.get(AccaHistoryRow, acca_id)
                if row2 is None:
                    verify_warning = "post_commit_select_acca_history_missing"
                    logger.error(
                        "PERSIST_ACCA_VERIFY_ERROR acca_id=%s %s (misma DATABASE_URL que escritura)",
                        acca_id,
                        verify_warning,
                    )
                else:
                    logger.info(
                        "PERSIST_ACCA_VERIFY_COMMITTED acca_id=%s found=True created_at=%s",
                        acca_id,
                        row2.created_at.isoformat() if row2.created_at else None,
                    )
    except Exception as exc:
        verify_warning = f"post_commit_verify_exception:{type(exc).__name__}:{exc}"
        logger.exception("PERSIST_ACCA_VERIFY_ERROR acca_id=%s", acca_id)

    logger.info("PERSIST_ACCA_SUCCESS acca_id=%s predictions_rows=%s", acca_id, len(picks_in))
    return acca_id, verify_warning


def fetch_acca_db_last_debug(settings: Settings) -> dict[str, Any]:
    """Diagnóstico: última ACCA, conteos, última prediction, hash de URL (no secreto completo)."""
    if not settings.database_url:
        return {
            "mode": "stateless",
            "database_url_hash": None,
            "detail": "DATABASE_URL no configurada",
        }
    url_hash = hashlib.sha256(settings.database_url.encode("utf-8")).hexdigest()[:16]
    try:
        with session_scope(settings.database_url) as db:
            if db is None:
                return {
                    "mode": "error",
                    "database_url_hash": url_hash,
                    "detail": "session_scope returned None (engine)",
                }
            total_accas = int(db.scalar(select(func.count()).select_from(AccaHistoryRow)) or 0)
            total_predictions = int(db.scalar(select(func.count()).select_from(PredictionRow)) or 0)
            last_acca = db.scalars(
                select(AccaHistoryRow).order_by(AccaHistoryRow.created_at.desc()).limit(1)
            ).first()
            last_pred = db.scalars(
                select(PredictionRow).order_by(PredictionRow.created_at.desc()).limit(1)
            ).first()
            return {
                "mode": "connected",
                "database_url_hash": url_hash,
                "total_acca_history": total_accas,
                "total_predictions": total_predictions,
                "last_acca": (
                    {
                        "acca_id": last_acca.acca_id,
                        "risk_profile": last_acca.risk_profile,
                        "fixture_date": last_acca.fixture_date.isoformat()
                        if last_acca.fixture_date
                        else None,
                        "total_odds": float(last_acca.total_odds),
                        "status": last_acca.status,
                        "created_at": last_acca.created_at.isoformat() if last_acca.created_at else None,
                    }
                    if last_acca
                    else None
                ),
                "last_prediction": (
                    {
                        "id": last_pred.id,
                        "acca_id": last_pred.acca_id,
                        "fixture_id": int(last_pred.fixture_id),
                        "market": last_pred.market,
                        "created_at": last_pred.created_at.isoformat() if last_pred.created_at else None,
                    }
                    if last_pred
                    else None
                ),
            }
    except Exception as exc:
        logger.exception("fetch_acca_db_last_debug")
        return {
            "mode": "error",
            "database_url_hash": url_hash,
            "detail": str(exc),
            "error_type": type(exc).__name__,
        }


def list_acca_history(
    settings: Settings,
    *,
    limit: int = 50,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    if not settings.database_url or user_id is None:
        return []
    limit = max(1, min(limit, 200))
    try:
        with session_scope(settings.database_url) as db:
            if db is None:
                return []
            stmt = (
                select(AccaHistoryRow)
                .where(AccaHistoryRow.user_id == user_id)
                .order_by(AccaHistoryRow.created_at.desc())
                .limit(limit)
            )
            rows = db.scalars(stmt).all()
            items: list[dict[str, Any]] = []
            for r in rows:
                picks = r.picks_json if isinstance(r.picks_json, list) else []
                st = getattr(r, "status", None) or "pending"
                items.append(
                    {
                        "id": r.acca_id,
                        "acca_id": r.acca_id,
                        "date": r.fixture_date.isoformat() if r.fixture_date else "",
                        "risk": r.risk_profile,
                        "risk_label": {
                            "low": "Bajo",
                            "medium": "Medio",
                            "high": "Alto",
                            "extreme": "Muy alto",
                        }.get(r.risk_profile, r.risk_profile),
                        "total_odds": float(r.total_odds),
                        "total_ev": float(r.combined_ev_pct),
                        "combined_ev_pct": float(r.combined_ev_pct),
                        "confidence": float(r.confidence_score),
                        "confidence_score": float(r.confidence_score),
                        "picks_count": len(picks),
                        "pick_count": len(picks),
                        "created_at": r.created_at.isoformat() if r.created_at else "",
                        "status": st if st in ("pending",) else "pending",
                        "model_version": r.model_version or "",
                    }
                )
            return items
    except Exception:
        logger.exception("list_acca_history: error al leer DB; se devuelve historial vacío.")
        return []
