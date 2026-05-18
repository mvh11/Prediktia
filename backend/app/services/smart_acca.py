"""
Smart ACCA Builder — versión simple y estable para demo de tesis.

Pipeline: pool de candidatos → filtro básico → top EV → N picks (fixture único) →
ajuste ligero de cuota combinada → salida.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from app.config import Settings
from app.services.acca_candidates import AccaCandidate, build_acca_candidate_pool
from app.services.acca_fixture_filter import filter_and_sort_fixtures_for_acca
from app.services.football_api import (
    extract_cache_meta,
    fetch_fixtures_by_date_cached,
    peek_fixtures_cache,
)
from app.services.league_priority import league_priority_score

logger = logging.getLogger(__name__)

RiskLevel = Literal["low", "medium", "high", "extreme"]


@dataclass(frozen=True)
class SimpleAccaProfile:
    exact_picks: int
    target_min: float
    target_max: float
    max_single_odds: float


SIMPLE_PROFILES: dict[RiskLevel, SimpleAccaProfile] = {
    "low": SimpleAccaProfile(exact_picks=2, target_min=1.8, target_max=4.5, max_single_odds=2.2),
    "medium": SimpleAccaProfile(exact_picks=3, target_min=3.0, target_max=10.0, max_single_odds=4.0),
    "high": SimpleAccaProfile(exact_picks=4, target_min=8.0, target_max=20.0, max_single_odds=8.0),
    "extreme": SimpleAccaProfile(exact_picks=5, target_min=15.0, target_max=40.0, max_single_odds=12.0),
}

# (min_prob, min_odds, max_odds, min_ev) — capas de relajación por perfil
FilterTier = tuple[float, float, float, float]


def _filter_tiers_for_risk(risk: RiskLevel, profile: SimpleAccaProfile) -> list[FilterTier]:
    if risk == "extreme":
        return [
            (0.28, 1.10, profile.max_single_odds, -0.05),
            (0.25, 1.08, profile.max_single_odds + 2.0, -0.08),
            (0.22, 1.05, profile.max_single_odds + 4.0, -0.12),
            (0.18, 1.05, 20.0, -0.15),
        ]
    if risk == "high":
        return [
            (0.35, 1.10, profile.max_single_odds, 0.0),
            (0.32, 1.08, profile.max_single_odds + 1.0, -0.01),
            (0.28, 1.05, profile.max_single_odds + 2.0, -0.03),
            (0.25, 1.05, 12.0, -0.06),
            (0.20, 1.05, 15.0, -0.10),
        ]
    if risk == "medium":
        return [
            (0.45, 1.15, profile.max_single_odds, 0.0),
            (0.40, 1.12, profile.max_single_odds + 0.5, 0.0),
            (0.35, 1.10, profile.max_single_odds + 1.0, 0.0),
            (0.30, 1.08, profile.max_single_odds + 2.0, -0.01),
        ]
    return [
        (0.45, 1.15, profile.max_single_odds, 0.0),
        (0.40, 1.12, profile.max_single_odds + 0.3, 0.0),
        (0.35, 1.10, profile.max_single_odds + 0.5, 0.0),
        (0.30, 1.08, profile.max_single_odds + 1.0, -0.01),
    ]

RISK_LABELS: dict[RiskLevel, str] = {
    "low": "Bajo",
    "medium": "Medio",
    "high": "Alto",
    "extreme": "Muy alto",
}


def _combined_odds(picks: list[AccaCandidate]) -> float:
    o = 1.0
    for p in picks:
        o *= p.metrics.cuota
    return round(o, 3)


def _combined_prob(picks: list[AccaCandidate]) -> float:
    p = 1.0
    for pick in picks:
        p *= pick.metrics.probabilidad
    return round(p, 6)


def _aggregate_scores(picks: list[AccaCandidate]) -> tuple[float, float, float]:
    if not picks:
        return 0.0, 0.0, 0.0
    conf = sum(p.metrics.confidence_pct for p in picks) / len(picks)
    vol = sum(p.volatility for p in picks) / len(picks)
    risk = min(
        100.0,
        vol * 55.0
        + (1.0 - conf / 100.0) * 35.0
        + min(25.0, math.log10(max(_combined_odds(picks), 1.01)) * 12.0),
    )
    return round(conf, 1), round(risk, 1), round(vol * 100.0, 1)


def _filter_pool(
    candidates: list[AccaCandidate],
    *,
    min_prob: float,
    min_odds: float,
    max_odds: float,
    min_ev: float,
) -> list[AccaCandidate]:
    out: list[AccaCandidate] = []
    for c in candidates:
        m = c.metrics
        if m.ev < min_ev:
            continue
        if m.probabilidad < min_prob:
            continue
        if m.cuota < min_odds or m.cuota > max_odds:
            continue
        out.append(c)
    return out


def _candidate_sort_key(c: AccaCandidate) -> tuple[float, float]:
    return (league_priority_score(c.league_id, c.liga, c.country), c.metrics.ev)


def _select_unique_by_ev(pool: list[AccaCandidate], n: int) -> list[AccaCandidate]:
    sorted_pool = sorted(pool, key=_candidate_sort_key, reverse=True)
    selected: list[AccaCandidate] = []
    fids: set[int] = set()
    for c in sorted_pool:
        if len(selected) >= n:
            break
        if c.fixture_id in fids:
            continue
        selected.append(c)
        fids.add(c.fixture_id)
    return selected


def build_extreme_acca(
    candidates: list[AccaCandidate],
    *,
    fixtures_in: int = 0,
) -> dict[str, Any]:
    """
    Perfil Muy alto: mínima lógica, siempre devuelve la mejor combinada posible.
    Filtros: prob > 0.20, cuota > 1.15. Sin ajuste agresivo de cuota combinada.
    """
    n = SIMPLE_PROFILES["extreme"].exact_picks
    profile = SIMPLE_PROFILES["extreme"]

    logger.info(
        "EXTREME_START candidates=%s fixtures_in=%s",
        len(candidates),
        fixtures_in,
    )

    def is_valid(c: AccaCandidate) -> bool:
        m = c.metrics
        return m.cuota > 1.15 and m.probabilidad > 0.20 and 1.01 <= m.cuota <= 25.0

    pool = [c for c in candidates if is_valid(c)]
    ordered = sorted(pool, key=_candidate_sort_key, reverse=True)

    selected: list[AccaCandidate] = []
    fids: set[int] = set()
    for c in ordered:
        if len(selected) >= n:
            break
        if c.fixture_id in fids:
            continue
        selected.append(c)
        fids.add(c.fixture_id)

    if len(selected) < n:
        for c in sorted(candidates, key=_candidate_sort_key, reverse=True):
            if len(selected) >= n:
                break
            if c.fixture_id in fids:
                continue
            m = c.metrics
            if m.cuota >= 1.05 and m.probabilidad >= 0.15:
                selected.append(c)
                fids.add(c.fixture_id)

    if not selected and candidates:
        logger.warning("EXTREME_EMPTY_FALLBACK using top fixtures by league+EV")
        for c in sorted(candidates, key=_candidate_sort_key, reverse=True):
            if len(selected) >= n:
                break
            if c.fixture_id in fids:
                continue
            if c.metrics.cuota >= 1.01:
                selected.append(c)
                fids.add(c.fixture_id)

    total_odds = _combined_odds(selected) if selected else 1.0
    combined_p = _combined_prob(selected)
    combined_ev = combined_p * total_odds - 1.0 if selected else 0.0
    conf, risk_score, vol_score = _aggregate_scores(selected)

    message: str | None = None
    if len(selected) >= n:
        message = (
            f"Combinada muy alto generada (@{total_odds:.2f}). "
            f"Objetivo orientativo {profile.target_min:.0f}–{profile.target_max:.0f}."
        )
    elif len(selected) > 0:
        message = (
            f"Combinada parcial muy alto: {len(selected)}/{n} picks (@{total_odds:.2f})."
        )
    else:
        message = "No hay suficientes partidos disponibles actualmente para armar esta combinada."

    logger.info(
        "EXTREME_FINAL picks=%s total_odds=%s",
        len(selected),
        total_odds,
    )

    return {
        "risk": "extreme",
        "risk_label": RISK_LABELS["extreme"],
        "profile": {
            "min_picks": n,
            "max_picks": n,
            "target_odds_range": f"{profile.target_min} – {profile.target_max}",
        },
        "picks": selected,
        "total_odds": total_odds,
        "combined_probability": combined_p,
        "combined_ev": round(combined_ev, 5),
        "combined_ev_pct": round(combined_ev * 100.0, 2),
        "confidence_score": conf,
        "risk_score": risk_score,
        "volatility_score": vol_score,
        "candidates_pool_size": len(candidates),
        "eligible_count": len(pool),
        "message": message,
        "risk_profile_validation": {
            "exact_picks_required": n,
            "exact_picks_met": len(selected) >= n,
            "fixtures_in_schedule": fixtures_in,
        },
    }


def _build_pool_with_relaxation(
    candidates: list[AccaCandidate],
    profile: SimpleAccaProfile,
    risk: RiskLevel,
) -> list[AccaCandidate]:
    """Capas de relajación hasta tener al menos exact_picks fixtures distintos."""
    for min_prob, min_odds, max_odds, min_ev in _filter_tiers_for_risk(risk, profile):
        pool = _filter_pool(
            candidates,
            min_prob=min_prob,
            min_odds=min_odds,
            max_odds=max_odds,
            min_ev=min_ev,
        )
        uniq_fixtures = len({c.fixture_id for c in pool})
        if uniq_fixtures >= profile.exact_picks:
            return pool
    # Último recurso: cuotas válidas; en alto/muy alto aceptamos EV bajo para completar demo
    min_ev_floor = -0.15 if risk in ("high", "extreme") else -0.05
    max_odds_cap = profile.max_single_odds + (8.0 if risk == "extreme" else 5.0)
    return [
        c
        for c in candidates
        if c.metrics.ev >= min_ev_floor
        and c.metrics.cuota >= 1.05
        and c.metrics.cuota <= max_odds_cap
    ]


def _fill_to_exact_picks(
    selected: list[AccaCandidate],
    candidates: list[AccaCandidate],
    n: int,
    *,
    risk: RiskLevel,
) -> list[AccaCandidate]:
    """Completa hasta N picks únicos por fixture; prioriza EV, luego probabilidad."""
    if len(selected) >= n:
        return selected[:n]
    work = list(selected)
    used: set[int] = {p.fixture_id for p in work}

    def rank(c: AccaCandidate) -> tuple[float, float]:
        return (c.metrics.ev, c.metrics.probabilidad)

    min_prob = 0.28 if risk == "extreme" else (0.35 if risk == "high" else 0.20)
    min_odds = 1.10 if risk in ("high", "extreme") else 1.05
    min_ev = -0.20 if risk == "extreme" else (-0.10 if risk == "high" else -0.05)

    ordered = sorted(candidates, key=rank, reverse=True)
    for c in ordered:
        if len(work) >= n:
            break
        if c.fixture_id in used:
            continue
        m = c.metrics
        if m.probabilidad < min_prob or m.cuota < min_odds or m.ev < min_ev:
            continue
        work.append(c)
        used.add(c.fixture_id)

    if len(work) < n:
        for c in ordered:
            if len(work) >= n:
                break
            if c.fixture_id in used:
                continue
            if c.metrics.cuota >= 1.05:
                work.append(c)
                used.add(c.fixture_id)

    return work[:n]


def _adjust_total_odds(
    selected: list[AccaCandidate],
    pool: list[AccaCandidate],
    profile: SimpleAccaProfile,
) -> list[AccaCandidate]:
    """Sustituye picks (mismo tamaño) para acercar la cuota combinada a la banda objetivo."""
    n = profile.exact_picks
    if len(selected) != n:
        return selected

    work = list(selected)
    min_t, max_t = profile.target_min, profile.target_max

    for _ in range(80):
        total = _combined_odds(work)
        if min_t <= total <= max_t:
            return work

        fids = {p.fixture_id for p in work}
        improved = False

        if total < min_t:
            replace_i = min(range(n), key=lambda i: work[i].metrics.cuota)
            current = work[replace_i].metrics.cuota
            best: AccaCandidate | None = None
            best_total = total
            for c in pool:
                if c.fixture_id in fids:
                    continue
                trial = list(work)
                trial[replace_i] = c
                t = _combined_odds(trial)
                if t > best_total and t <= max_t * 1.05:
                    best = c
                    best_total = t
            if best is not None:
                work[replace_i] = best
                fids = {p.fixture_id for p in work}
                improved = True

        elif total > max_t:
            replace_i = max(range(n), key=lambda i: work[i].metrics.cuota)
            current = work[replace_i].metrics.cuota
            best: AccaCandidate | None = None
            best_total = total
            for c in pool:
                if c.fixture_id in fids:
                    continue
                if c.metrics.cuota >= current:
                    continue
                trial = list(work)
                trial[replace_i] = c
                t = _combined_odds(trial)
                if t < best_total and t >= min_t * 0.95:
                    best = c
                    best_total = t
            if best is not None:
                work[replace_i] = best
                fids = {p.fixture_id for p in work}
                improved = True

        if not improved:
            break

    return work


def build_simple_acca(
    candidates: list[AccaCandidate],
    risk: RiskLevel,
    *,
    fixtures_in: int = 0,
) -> dict[str, Any]:
    if risk == "extreme":
        return build_extreme_acca(candidates, fixtures_in=fixtures_in)

    profile = SIMPLE_PROFILES[risk]
    n = profile.exact_picks

    logger.info(
        "RISK_PROFILE_START risk=%s exact_picks=%s target=[%.2f,%.2f] fixtures_in=%s candidates_total=%s",
        risk,
        n,
        profile.target_min,
        profile.target_max,
        fixtures_in,
        len(candidates),
    )

    pool = _build_pool_with_relaxation(candidates, profile, risk)
    eligible_count = len(pool)
    top = sorted(pool, key=lambda c: c.metrics.ev, reverse=True)[:10]
    logger.info(
        "ELIGIBLE_STAGE risk=%s eligible_count=%s top10=%s",
        risk,
        eligible_count,
        " | ".join(
            f"fid={c.fixture_id} cuota={c.metrics.cuota:.2f} p={c.metrics.probabilidad:.3f} "
            f"ev={c.metrics.ev:.4f} conf={c.metrics.confidence_pct:.0f}"
            for c in top
        )
        or "(none)",
    )

    selected = _select_unique_by_ev(pool, n)
    logger.info(
        "GREEDY_STAGE risk=%s picks_selected=%s combined_odds=%s",
        risk,
        len(selected),
        _combined_odds(selected) if selected else 1.0,
    )

    if len(selected) < n:
        logger.info("FILL_STAGE risk=%s filling_from_candidates", risk)
        selected = _fill_to_exact_picks(selected, pool if pool else candidates, n, risk=risk)

    before_adj = list(selected)
    adjust_pool = pool if pool else candidates
    if len(selected) == n:
        selected = _adjust_total_odds(selected, adjust_pool, profile)
    logger.info(
        "ADJUST_STAGE risk=%s before_odds=%s after_odds=%s picks=%s",
        risk,
        _combined_odds(before_adj) if before_adj else 1.0,
        _combined_odds(selected) if selected else 1.0,
        len(selected),
    )

    total_odds = _combined_odds(selected) if selected else 1.0
    combined_p = _combined_prob(selected)
    combined_ev = combined_p * total_odds - 1.0 if selected else 0.0
    conf, risk_score, vol_score = _aggregate_scores(selected)

    insufficient = len(selected) < n
    message: str | None = None
    if insufficient:
        message = (
            "No hay suficientes partidos disponibles actualmente para armar esta combinada. "
            f"Se encontraron {len(selected)} de {n} picks requeridos."
        )
    elif not (profile.target_min <= total_odds <= profile.target_max):
        message = (
            f"Combinada generada con cuota @{total_odds:.2f} "
            f"(objetivo {profile.target_min:.1f}–{profile.target_max:.1f})."
        )

    logger.info(
        "FINAL_STAGE risk=%s picks=%s total_odds=%s combined_p=%s combined_ev_pct=%.2f conf=%s ok=%s",
        risk,
        len(selected),
        total_odds,
        combined_p,
        combined_ev * 100.0,
        conf,
        not insufficient and len(selected) >= n,
    )

    return {
        "risk": risk,
        "risk_label": RISK_LABELS[risk],
        "profile": {
            "min_picks": n,
            "max_picks": n,
            "target_odds_range": f"{profile.target_min} – {profile.target_max}",
        },
        "picks": selected,
        "total_odds": total_odds,
        "combined_probability": combined_p,
        "combined_ev": round(combined_ev, 5),
        "combined_ev_pct": round(combined_ev * 100.0, 2),
        "confidence_score": conf,
        "risk_score": risk_score,
        "volatility_score": vol_score,
        "candidates_pool_size": len(candidates),
        "eligible_count": eligible_count,
        "message": message,
        "risk_profile_validation": {
            "exact_picks_required": n,
            "exact_picks_met": len(selected) == n,
            "fixtures_in_schedule": fixtures_in,
        },
    }


def resolve_acca_calendar_day_for_pre_match(
    settings: Settings,
    requested: date,
    *,
    now_utc: datetime | None = None,
    max_extra_days: int = 1,
) -> tuple[date, int, bool]:
    """
    Elige el día con más fixtures pre-partido entre hoy y hasta +max_extra_days.
    Reutiliza caché en memoria; como máximo 2 peticiones HTTP en frío (hoy + mañana).
    """
    now = now_utc or datetime.now(timezone.utc)
    best_day = requested
    best_count = 0
    scan_days = min(max_extra_days, 1) + 1

    for offset in range(scan_days):
        day = requested + timedelta(days=offset)
        peeked = peek_fixtures_cache(day)
        if peeked is not None:
            payload = peeked
        else:
            payload = fetch_fixtures_by_date_cached(settings, day)

        fixtures = payload.get("response") or []
        if not isinstance(fixtures, list):
            fixtures = []
        filtered, _, _ = filter_and_sort_fixtures_for_acca(
            fixtures,
            now_utc=now,
            min_minutes_before_kickoff=settings.acca_min_minutes_before_kickoff,
            emit_trace_log=False,
        )
        n = len(filtered)
        if n > best_count:
            best_count = n
            best_day = day

    return best_day, best_count, best_day > requested


def generate_acca_for_date(
    settings: Settings,
    day: date,
    risk: RiskLevel,
    *,
    fetch_odds: bool = True,
) -> dict[str, Any]:
    payload = fetch_fixtures_by_date_cached(settings, day)
    upstream_meta = extract_cache_meta(payload)
    fixtures = payload.get("response") or []
    if not isinstance(fixtures, list):
        fixtures = []

    logger.info(
        "ACCA_GENERATE date=%s upstream_fixtures=%s risk=%s",
        day.isoformat(),
        len(fixtures),
        risk,
    )

    now_utc = datetime.now(timezone.utc)
    filtered, schedule_discard, filter_meta = filter_and_sort_fixtures_for_acca(
        fixtures,
        now_utc=now_utc,
        min_minutes_before_kickoff=settings.acca_min_minutes_before_kickoff,
    )

    max_fx = 120 if risk in ("high", "extreme") else 72
    fetch_eff = fetch_odds
    if risk == "extreme":
        # Evita timeouts por muchas llamadas a /odds; cuotas sintéticas estables.
        fetch_eff = False
    pool = build_acca_candidate_pool(
        filtered,
        settings,
        fetch_odds=fetch_eff,
        max_fixtures=max_fx,
        now_utc=now_utc,
    )

    built = build_simple_acca(pool, risk, fixtures_in=len(filtered))
    selected: list[AccaCandidate] = built["picks"]

    picks_out = []
    for p in selected:
        m = p.metrics
        picks_out.append(
            {
                "fixture_id": p.fixture_id,
                "liga": p.liga,
                "equipo_local": p.equipo_local,
                "equipo_visitante": p.equipo_visitante,
                "fecha": p.fecha,
                "kickoff_in_minutes": p.kickoff_in_minutes,
                "mercado": p.mercado,
                "pick": p.pick,
                "cuota": m.cuota,
                "probabilidad": m.probabilidad,
                "ev": m.ev,
                "ev_pct": m.ev_pct,
                "edge_pct": m.edge_pct,
                "confidence_pct": m.confidence_pct,
                "implied_probability": m.implied_probability,
                "odds_source": p.odds_source,
            }
        )

    bookmaker_picks = sum(1 for x in picks_out if x["odds_source"] == "bookmaker")
    unique_fids = {int(x["fixture_id"]) for x in picks_out if isinstance(x.get("fixture_id"), int)}

    return {
        "date": day.isoformat(),
        "model_version": "poisson-v1+ev-simple",
        "risk": built["risk"],
        "risk_label": built["risk_label"],
        "profile": built["profile"],
        "picks": picks_out,
        "pick_count": len(picks_out),
        "total_odds": built["total_odds"],
        "combined_probability": built["combined_probability"],
        "combined_ev": built["combined_ev"],
        "combined_ev_pct": built["combined_ev_pct"],
        "confidence_score": built["confidence_score"],
        "risk_score": built["risk_score"],
        "volatility_score": built["volatility_score"],
        "message": built.get("message"),
        "meta": {
            "candidates_pool_size": built["candidates_pool_size"],
            "eligible_after_filters": built["eligible_count"],
            "bookmaker_odds_picks": bookmaker_picks,
            "independence_assumption": "P(combinada) ≈ ∏ P(picks).",
            "fetch_odds": fetch_odds,
            "fixtures_upstream_total": len(fixtures),
            "fixtures_after_schedule_filter": len(filtered),
            "fixtures_after_schedule_strict": filter_meta.get("fixtures_after_schedule_strict", 0),
            "schedule_filter_fallback": filter_meta.get("schedule_filter_fallback", False),
            "schedule_discard_reasons": schedule_discard,
            "fixtures_source": "api_football",
            "requested_date": day.isoformat(),
            "resolved_date": day.isoformat(),
            "auto_shifted_date": False,
            "unique_fixtures_count": len(unique_fids),
            "risk_profile_validation": built.get("risk_profile_validation") or {},
            "persist_status": "not_attempted",
            "persist_error": None,
            "upstream_warning": upstream_meta.warning,
            "cache_stale": upstream_meta.stale,
        },
    }


# Compatibilidad con imports existentes
build_smart_acca = build_simple_acca
