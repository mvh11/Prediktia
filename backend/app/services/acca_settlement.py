"""
Liquidación automática de ACCAs pendientes usando resultados finales API-Football.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select

from app.config import Settings
from app.db.models import AccaHistoryRow
from app.db.session import session_scope
from app.services.football_api import FootballApiError, fetch_fixtures_by_ids

logger = logging.getLogger(__name__)

AccaOutcome = Literal["pending", "won", "lost"]
FINISHED_STATUSES = frozenset({"FT", "AET", "PEN"})


def _fixture_id_from_item(item: dict[str, Any]) -> int | None:
    fx = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    fid = fx.get("id")
    return int(fid) if isinstance(fid, int) else None


def _status_short(item: dict[str, Any]) -> str | None:
    fx = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    st = fx.get("status") if isinstance(fx.get("status"), dict) else {}
    s = st.get("short")
    return str(s).strip().upper() if isinstance(s, str) else None


def _fulltime_goals(item: dict[str, Any]) -> tuple[int | None, int | None]:
    """Goles finales del partido (usa `goals` y cae a score.fulltime)."""
    g = item.get("goals") if isinstance(item.get("goals"), dict) else {}
    h = g.get("home")
    a = g.get("away")
    if isinstance(h, int) and isinstance(a, int):
        return h, a
    sc = item.get("score") if isinstance(item.get("score"), dict) else {}
    ft = sc.get("fulltime") if isinstance(sc.get("fulltime"), dict) else {}
    h2 = ft.get("home")
    a2 = ft.get("away")
    if h2 is None and isinstance(ft.get("home"), str) and str(ft["home"]).isdigit():
        h2 = int(ft["home"])
    if a2 is None and isinstance(ft.get("away"), str) and str(ft["away"]).isdigit():
        a2 = int(ft["away"])
    if isinstance(h2, int) and isinstance(a2, int):
        return h2, a2
    return None, None


def _norm(s: str) -> str:
    return s.strip().lower()


def evaluate_pick_result(
    pick: dict[str, Any],
    fixture_item: dict[str, Any] | None,
) -> bool | None:
    """
    Evalúa un pick contra el fixture upstream (API-Football).
    True = acierto, False = fallo, None = partido no terminado o mercado no soportado.
    """
    if not isinstance(pick, dict) or fixture_item is None:
        return None
    st = _status_short(fixture_item)
    if st not in FINISHED_STATUSES:
        return None
    hg, ag = _fulltime_goals(fixture_item)
    if hg is None or ag is None:
        return None

    mercado = _norm(str(pick.get("mercado") or ""))
    pick_label = _norm(str(pick.get("pick") or ""))
    total = hg + ag

    if mercado == "1x2":
        if pick_label in ("victoria local", "local", "home", "1"):
            return hg > ag
        if pick_label in ("empate", "draw", "x"):
            return hg == ag
        if pick_label in ("victoria visitante", "visitante", "away", "2"):
            return ag > hg
        return None

    if "doble" in mercado or mercado in ("doble oportunidad", "double chance"):
        if pick_label in ("1x", "1 or x", "1 or draw"):
            return hg >= ag
        if pick_label in ("x2", "x or 2", "draw or away"):
            return ag >= hg
        if pick_label in ("12", "1 or 2", "home or away"):
            return hg != ag
        return None

    if "total" in mercado or "goles" in mercado or mercado in ("total goles",):
        if "más" in pick_label or "over" in pick_label or pick_label.startswith("over"):
            return total > 2
        if "menos" in pick_label or "under" in pick_label or pick_label.startswith("under"):
            return total < 3
        return None

    if mercado in ("ambos marcan", "btts", "both teams") or "ambos" in mercado:
        if pick_label in ("sí", "si", "yes", "y"):
            return hg >= 1 and ag >= 1
        if pick_label in ("no", "n"):
            return hg == 0 or ag == 0
        return None

    return None


def calculate_acca_result(pick_results: list[bool | None]) -> AccaOutcome:
    """Agrega resultados por pick: pending si falta alguno; won si todos True; lost en otro caso."""
    if not pick_results:
        return "pending"
    if any(x is None for x in pick_results):
        return "pending"
    if all(x is True for x in pick_results):
        return "won"
    return "lost"


def calculate_acca_roi(total_odds: float, outcome: AccaOutcome) -> float | None:
    if outcome == "won":
        return float(total_odds) - 1.0
    if outcome == "lost":
        return -1.0
    return None


def settle_pending_accas(settings: Settings) -> dict[str, Any]:
    """
    Busca ACCAs pending, consulta API-Football por fixtures de los picks y liquida won/lost + ROI + settled_at.
    """
    if not settings.database_url:
        return {
            "ok": False,
            "reason": "no_database",
            "processed": 0,
            "settled": [],
            "skipped": [],
            "errors": [],
        }

    settled: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    try:
        with session_scope(settings.database_url) as db:
            if db is None:
                return {
                    "ok": False,
                    "reason": "session_unavailable",
                    "processed": 0,
                    "settled": [],
                    "skipped": [],
                    "errors": [],
                }
            stmt = select(AccaHistoryRow).where(AccaHistoryRow.status == "pending")
            rows = db.scalars(stmt).all()

            for row in rows:
                acca_id = row.acca_id
                picks = row.picks_json if isinstance(row.picks_json, list) else []
                picks_dicts = [p for p in picks if isinstance(p, dict)]
                if not picks_dicts:
                    skipped.append({"acca_id": acca_id, "reason": "no_picks"})
                    continue

                fids: list[int] = []
                for p in picks_dicts:
                    fid = p.get("fixture_id")
                    if isinstance(fid, int):
                        fids.append(fid)
                if not fids:
                    skipped.append({"acca_id": acca_id, "reason": "no_fixture_ids"})
                    continue

                try:
                    payload = fetch_fixtures_by_ids(settings, fids)
                except FootballApiError as exc:
                    errors.append({"acca_id": acca_id, "reason": str(exc)})
                    continue

                by_id: dict[int, dict[str, Any]] = {}
                for item in payload.get("response") or []:
                    if not isinstance(item, dict):
                        continue
                    fid = _fixture_id_from_item(item)
                    if fid is not None:
                        by_id[fid] = item

                pick_results: list[bool | None] = []
                for p in picks_dicts:
                    fid = p.get("fixture_id")
                    if not isinstance(fid, int):
                        pick_results.append(None)
                        continue
                    item = by_id.get(fid)
                    if item is None:
                        pick_results.append(None)
                        continue
                    r = evaluate_pick_result(p, item)
                    pick_results.append(r)

                outcome = calculate_acca_result(pick_results)
                if outcome == "pending":
                    skipped.append({"acca_id": acca_id, "reason": "still_pending"})
                    continue

                roi = calculate_acca_roi(row.total_odds, outcome)
                now = datetime.now(timezone.utc)
                row.status = outcome
                row.result = outcome
                row.roi = float(roi) if roi is not None else None
                row.settled_at = now
                settled.append(
                    {
                        "acca_id": acca_id,
                        "status": outcome,
                        "roi": roi,
                        "picks": len(pick_results),
                    }
                )
                logger.info(
                    "ACCA_AUTO_SETTLE acca_id=%s status=%s roi=%s picks=%s",
                    acca_id,
                    outcome,
                    roi,
                    len(pick_results),
                )
    except Exception as exc:
        logger.exception("settle_pending_accas: error global")
        errors.append({"acca_id": "*", "reason": str(exc)})
        return {
            "ok": False,
            "reason": "exception",
            "processed": len(settled),
            "settled": settled,
            "skipped": skipped,
            "errors": errors,
        }

    return {
        "ok": True,
        "reason": None,
        "processed": len(settled),
        "settled": settled,
        "skipped": skipped,
        "errors": errors,
    }
