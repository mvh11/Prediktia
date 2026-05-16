"""
Filtro de fixtures para ACCA: estados NS/TBD + kickoff futuro en UTC.

Reglas de tiempo:
- Si existe `fixture.timestamp`, es la ÚNICA fuente de verdad (Unix → UTC vía fromtimestamp).
  No se reinterpreta con `fixture.date` ni con TZ local del servidor.
- Si timestamp > 9999999999 se asume milisegundos y se divide por 1000.
- `fixture.date` solo se usa si no hay timestamp válido (fallback ISO → UTC).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

INFO_TRACE_LIMIT = 20


def kickoff_parse_source(item: dict[str, Any]) -> str:
    """Si el kickoff se basa en timestamp Unix normalizado o en fallback date ISO."""
    fx = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    if _normalize_fixture_timestamp(fx.get("timestamp")) is not None:
        return "timestamp"
    raw = fx.get("date")
    if isinstance(raw, str) and raw.strip():
        return "date"
    return "none"


def _final_reject_reason(
    raw: dict[str, Any],
    now_utc: datetime,
    min_margin: int,
    *,
    eligible_ids: set[int],
) -> tuple[bool, str | None]:
    fid = _fixture_id(raw)
    if fid is not None and fid in eligible_ids:
        return True, None
    st_r = fixture_status_reason(raw)
    if st_r:
        return False, st_r
    ks = fixture_kickoff_reason_strict(raw, now_utc, min_margin)
    if ks:
        return False, ks
    kr = fixture_kickoff_reason_relaxed(raw, now_utc)
    if kr:
        return False, kr
    return False, "excluded_from_pool"


def build_acca_fixture_trace_row(
    raw: dict[str, Any],
    now_utc: datetime,
    min_margin: int,
    eligible_ids: set[int],
) -> dict[str, Any]:
    fx = raw.get("fixture") if isinstance(raw.get("fixture"), dict) else {}
    fid = _fixture_id(raw)
    raw_ts = fx.get("timestamp")
    raw_date = fx.get("date")
    kick = parse_fixture_kickoff_utc(raw)
    mins = kickoff_in_minutes_from_now(raw, now_utc)
    status = _status_short(raw) or ""
    accepted, rreason = _final_reject_reason(raw, now_utc, min_margin, eligible_ids=eligible_ids)
    return {
        "fixture_id": fid,
        "raw_timestamp": raw_ts,
        "raw_date": raw_date,
        "parse_source": kickoff_parse_source(raw),
        "parsed_kickoff_utc": kick.isoformat() if kick else None,
        "now_utc": now_utc.isoformat(),
        "status": status,
        "diff_minutes": mins,
        "accepted": accepted,
        "reject_reason": rreason,
    }


def log_acca_filter_trace_batch(
    fixtures: list[Any],
    eligible: list[dict[str, Any]],
    now_utc: datetime,
    min_margin: int,
    *,
    limit: int = INFO_TRACE_LIMIT,
) -> None:
    eligible_ids = {_fixture_id(x) for x in eligible if _fixture_id(x) is not None}
    logged = 0
    for raw in fixtures:
        if not isinstance(raw, dict):
            continue
        if logged >= limit:
            break
        row = build_acca_fixture_trace_row(raw, now_utc, min_margin, eligible_ids)
        logger.info(
            "ACCA_FILTER_TRACE fixture_id=%s raw_timestamp=%r parsed_kickoff_utc=%s now_utc=%s status=%r "
            "accepted=%s reject_reason=%s parse_source=%s diff_minutes=%s",
            row["fixture_id"],
            row["raw_timestamp"],
            row["parsed_kickoff_utc"],
            row["now_utc"],
            row["status"],
            row["accepted"],
            row["reject_reason"] or "",
            row["parse_source"],
            row["diff_minutes"],
        )
        logged += 1


STATUS_REJECTED: frozenset[str] = frozenset(
    {
        "FT",
        "AET",
        "PEN",
        "CANC",
        "PST",
        "ABD",
        "AWD",
        "WO",
        "LIVE",
        "1H",
        "HT",
        "2H",
        "ET",
        "BT",
    }
)

STATUS_ALLOWED_PREMATCH: frozenset[str] = frozenset({"NS", "TBD"})


def _status_short(item: dict[str, Any]) -> str:
    fx = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    st = fx.get("status") if isinstance(fx.get("status"), dict) else {}
    raw = st.get("short")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().upper()
    return ""


def _fixture_teams_label(item: dict[str, Any]) -> str:
    teams = item.get("teams") if isinstance(item.get("teams"), dict) else {}
    home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
    away = teams.get("away") if isinstance(teams.get("away"), dict) else {}
    h = (home.get("name") or "?").strip()
    a = (away.get("name") or "?").strip()
    return f"{h} vs {a}"


def _fixture_id(item: dict[str, Any]) -> int | None:
    fx = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    fid = fx.get("id")
    return int(fid) if isinstance(fid, int) else None


def _normalize_fixture_timestamp(raw_ts: Any) -> int | None:
    """Devuelve Unix segundos o None. API puede enviar segundos o milisegundos (int/float/str)."""
    if raw_ts is None:
        return None
    try:
        if isinstance(raw_ts, str):
            s = raw_ts.strip()
            if not s:
                return None
            ts = int(float(s))
        elif isinstance(raw_ts, (int, float)):
            ts = int(raw_ts)
        else:
            return None
    except (TypeError, ValueError):
        return None
    if ts <= 0:
        return None
    if ts > 9999999999:
        ts = ts // 1000
    return ts


def _kickoff_from_timestamp_only(item: dict[str, Any]) -> datetime | None:
    """Solo timestamp; no usa fixture.date."""
    fx = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    ts = _normalize_fixture_timestamp(fx.get("timestamp"))
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _kickoff_from_date_fallback(item: dict[str, Any]) -> datetime | None:
    """Solo si no hay timestamp válido: parse ISO de fixture.date → UTC (sin TZ local Windows)."""
    fx = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    raw = fx.get("date")
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


def parse_fixture_kickoff_utc(item: dict[str, Any]) -> datetime | None:
    """
    Kickoff UTC: timestamp Unix si existe; si no, fallback a fixture.date (ISO).
    """
    kt = _kickoff_from_timestamp_only(item)
    if kt is not None:
        return kt
    return _kickoff_from_date_fallback(item)


def fixture_status_reason(item: dict[str, Any]) -> str | None:
    short = _status_short(item)
    if short in STATUS_REJECTED:
        return f"excluded_status:{short}"
    if short in STATUS_ALLOWED_PREMATCH:
        return None
    if short == "":
        return None
    return f"non_allowed_status:{short}"


def fixture_kickoff_reason_strict(
    item: dict[str, Any], now_utc: datetime, min_minutes_before: int
) -> str | None:
    kick = parse_fixture_kickoff_utc(item)
    if kick is None:
        return "invalid_kickoff"
    if kick <= now_utc:
        return "kickoff_passed"
    if min_minutes_before > 0:
        buffer_end = now_utc + timedelta(minutes=min_minutes_before)
        if kick <= buffer_end:
            return f"kickoff_within_{min_minutes_before}m"
    return None


def fixture_kickoff_reason_relaxed(item: dict[str, Any], now_utc: datetime) -> str | None:
    kick = parse_fixture_kickoff_utc(item)
    if kick is None:
        return "invalid_kickoff"
    if kick <= now_utc:
        return "kickoff_passed"
    return None


def kickoff_in_minutes_from_now(item: dict[str, Any], now_utc: datetime) -> int | None:
    kick = parse_fixture_kickoff_utc(item)
    if kick is None:
        return None
    return int((kick - now_utc).total_seconds() / 60)


def _log_acca_fixture_comparison(
    item: dict[str, Any],
    now_utc: datetime,
    *,
    accepted: bool,
    reason: str,
) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    fx = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    raw_ts = fx.get("timestamp")
    raw_date = fx.get("date")
    kick = parse_fixture_kickoff_utc(item)
    mins = kickoff_in_minutes_from_now(item, now_utc)
    logger.debug(
        "now_utc=%s | fixture_timestamp=%s | fixture_date_raw=%s | parsed_kickoff_utc=%s | "
        "minutes_to_kickoff=%s | status_short=%s | accepted=%s | reason=%s",
        now_utc.isoformat(),
        repr(raw_ts),
        repr(raw_date),
        kick.isoformat() if kick else "None",
        mins if mins is not None else "None",
        _status_short(item) or "∅",
        accepted,
        reason,
    )


def _count_upstream_allowed_status(fixtures: list[Any]) -> int:
    n = 0
    for raw in fixtures:
        if isinstance(raw, dict) and fixture_status_reason(raw) is None:
            n += 1
    return n


def filter_and_sort_fixtures_for_acca(
    fixtures: list[Any],
    *,
    now_utc: datetime | None = None,
    min_minutes_before_kickoff: int = 0,
    league_quality_fn: Any = None,
    liquidity_fn: Any = None,
    emit_trace_log: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, Any]]:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    def default_lq(it: dict[str, Any]) -> float:
        league = it.get("league") if isinstance(it.get("league"), dict) else {}
        lid = int(league.get("id")) if isinstance(league.get("id"), int) else 0
        name = (league.get("name") or "").strip()
        country = (league.get("country") or "").strip()
        if league_quality_fn:
            return float(league_quality_fn(lid, name, country))
        from app.services.acca_candidates import _league_quality_score

        return _league_quality_score(lid, name, country)

    def default_liq(it: dict[str, Any]) -> float:
        league = it.get("league") if isinstance(it.get("league"), dict) else {}
        lid = int(league.get("id")) if isinstance(league.get("id"), int) else 0
        if liquidity_fn:
            return float(liquidity_fn(lid))
        from app.services.acca_candidates import TIER_S_IDS

        return 1.0 if lid in TIER_S_IDS else 0.55

    def sort_key(it: dict[str, Any]) -> tuple:
        kick = parse_fixture_kickoff_utc(it)
        k = kick.timestamp() if kick else float("inf")
        lq = default_lq(it)
        liq = default_liq(it)
        return (k, -lq, -liq)

    discard_counts: dict[str, int] = {}
    strict_eligible: list[dict[str, Any]] = []

    for raw in fixtures:
        if not isinstance(raw, dict):
            continue
        st_r = fixture_status_reason(raw)
        if st_r:
            discard_counts[st_r] = discard_counts.get(st_r, 0) + 1
            _log_acca_fixture_comparison(raw, now, accepted=False, reason=st_r)
            continue
        k_r = fixture_kickoff_reason_strict(raw, now, min_minutes_before_kickoff)
        if k_r:
            discard_counts[k_r] = discard_counts.get(k_r, 0) + 1
            _log_acca_fixture_comparison(raw, now, accepted=False, reason=k_r)
            continue
        strict_eligible.append(raw)
        _log_acca_fixture_comparison(raw, now, accepted=True, reason="strict_ok")

    strict_eligible.sort(key=sort_key)
    fallback_used = False
    eligible = list(strict_eligible)

    if not eligible:
        upstream_ok = _count_upstream_allowed_status(fixtures)
        if upstream_ok > 0:
            logger.warning(
                "strict filter rejected all fixtures; fallback enabled | upstream_NS_TBD=%s margin_min=%s",
                upstream_ok,
                min_minutes_before_kickoff,
            )
            fallback_used = True
            for raw in fixtures:
                if not isinstance(raw, dict):
                    continue
                st_r = fixture_status_reason(raw)
                if st_r:
                    continue
                k2 = fixture_kickoff_reason_relaxed(raw, now)
                if k2:
                    key = f"fallback_{k2}"
                    discard_counts[key] = discard_counts.get(key, 0) + 1
                    _log_acca_fixture_comparison(raw, now, accepted=False, reason=key)
                    continue
                eligible.append(raw)
                _log_acca_fixture_comparison(raw, now, accepted=True, reason="fallback_ok")
            eligible.sort(key=sort_key)
        else:
            logger.info(
                "acca_fixture_filter: strict filter 0 fixtures y 0 NS/TBD upstream (todos excluidos por estado)."
            )

    meta = {
        "schedule_filter_fallback": fallback_used,
        "fixtures_after_schedule_strict": len(strict_eligible),
    }
    logger.info(
        "acca_fixture_filter: upstream=%s strict_ok=%s final_ok=%s fallback=%s",
        len(fixtures),
        len(strict_eligible),
        len(eligible),
        fallback_used,
    )
    if emit_trace_log:
        log_acca_filter_trace_batch(
            fixtures,
            eligible,
            now,
            min_minutes_before_kickoff,
        )
    return eligible, discard_counts, meta


def build_acca_filter_debug_report(
    fixtures: list[Any],
    *,
    now_utc: datetime | None = None,
    min_minutes_before_kickoff: int = 0,
) -> dict[str, Any]:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    dict_fixtures = [x for x in fixtures if isinstance(x, dict)]
    total = len(dict_fixtures)
    eligible, reasons, meta = filter_and_sort_fixtures_for_acca(
        dict_fixtures,
        now_utc=now,
        min_minutes_before_kickoff=min_minutes_before_kickoff,
    )
    eligible_ids = {_fixture_id(x) for x in eligible if _fixture_id(x) is not None}

    sample_accepted: list[dict[str, Any]] = []
    sample_rejected: list[dict[str, Any]] = []

    for raw in dict_fixtures:
        fid = _fixture_id(raw)
        if fid is not None and fid in eligible_ids:
            if len(sample_accepted) < 20:
                kick = parse_fixture_kickoff_utc(raw)
                sample_accepted.append(
                    {
                        "fixture_id": fid,
                        "match": _fixture_teams_label(raw),
                        "status": _status_short(raw) or "∅",
                        "kickoff_utc": kick.isoformat() if kick else None,
                        "minutes_to_kickoff": kickoff_in_minutes_from_now(raw, now),
                        "accepted": True,
                        "reason": "fallback_ok" if meta.get("schedule_filter_fallback") else "strict_ok",
                    }
                )
            continue

        if len(sample_rejected) >= 20:
            continue
        st_r = fixture_status_reason(raw)
        if st_r:
            reason = st_r
        else:
            ks = fixture_kickoff_reason_strict(raw, now, min_minutes_before_kickoff)
            if ks:
                reason = ks
            else:
                kr = fixture_kickoff_reason_relaxed(raw, now)
                reason = kr or "unknown"
        kick = parse_fixture_kickoff_utc(raw)
        sample_rejected.append(
            {
                "fixture_id": fid,
                "match": _fixture_teams_label(raw),
                "status": _status_short(raw) or "∅",
                "kickoff_utc": kick.isoformat() if kick else None,
                "minutes_to_kickoff": kickoff_in_minutes_from_now(raw, now),
                "accepted": False,
                "reason": reason,
            }
        )

    return {
        "fixtures_total": total,
        "fixtures_pre_match": len(eligible),
        "fixtures_after_schedule_strict": meta.get("fixtures_after_schedule_strict", 0),
        "schedule_filter_fallback": meta.get("schedule_filter_fallback", False),
        "fixtures_rejected": max(0, total - len(eligible)),
        "reasons_count": reasons,
        "sample_accepted": sample_accepted,
        "sample_rejected": sample_rejected,
    }


def build_acca_filter_raw_rows(
    fixtures: list[Any],
    *,
    now_utc: datetime | None = None,
    min_minutes_before_kickoff: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Primeros `limit` fixtures con diagnóstico crudo UTC (GET /debug/acca-filter/raw)."""
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    dict_fixtures = [x for x in fixtures if isinstance(x, dict)]
    eligible, _, _ = filter_and_sort_fixtures_for_acca(
        dict_fixtures,
        now_utc=now,
        min_minutes_before_kickoff=min_minutes_before_kickoff,
        emit_trace_log=False,
    )
    eligible_ids = {_fixture_id(x) for x in eligible if _fixture_id(x) is not None}

    rows: list[dict[str, Any]] = []
    for raw in dict_fixtures[:limit]:
        row = build_acca_fixture_trace_row(
            raw, now, min_minutes_before_kickoff, eligible_ids
        )
        row["teams"] = _fixture_teams_label(raw)
        rows.append(row)

    return {
        "now_utc": now.isoformat(),
        "min_minutes_before_kickoff": min_minutes_before_kickoff,
        "rows": rows,
        "fixtures_total_upstream": len(dict_fixtures),
        "fixtures_pre_match_after_filter": len(eligible),
    }
