"""
Smart ACCA Builder: selección de combinadas por perfil de riesgo.

Pipeline explícito (logs por etapa):
  candidate_pool → eligible → assembly (producto mínimo bajo tope) → enhance →
  shrink (nunca baja de min_picks) → fill → repair → trim → garantía final.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from collections.abc import Callable
from typing import Any, Literal

from app.config import Settings
from app.services.acca_candidates import AccaCandidate, build_acca_candidate_pool, candidate_is_minor
from app.services.acca_fixture_filter import filter_and_sort_fixtures_for_acca
from app.services.football_api import fetch_fixtures_by_date_cached

logger = logging.getLogger(__name__)

RiskLevel = Literal["low", "medium", "high", "extreme"]


@dataclass(frozen=True)
class RiskProfile:
    min_picks: int
    max_picks: int
    min_prob: float
    min_ev: float
    min_single_odds: float
    max_single_odds: float
    target_total_odds_min: float
    target_total_odds_max: float
    max_volatility: float
    min_confidence_pct: float
    avoid_minor_leagues: bool
    avoid_volatile_markets: bool
    allow_underdogs: bool
    max_picks_per_league: int
    preferred_markets: frozenset[str]
    exceptional_odds_min: float | None = None
    max_exceptional_picks: int = 0
    exceptional_min_ev: float = 0.12
    exceptional_min_edge_pct: float = 12.0
    exceptional_max_odds_cap: float = 15.0
    min_combined_probability: float | None = None


RISK_PROFILES: dict[RiskLevel, RiskProfile] = {
    "low": RiskProfile(
        min_picks=2,
        max_picks=4,
        min_prob=0.52,
        min_ev=0.003,
        min_single_odds=1.08,
        max_single_odds=2.20,
        target_total_odds_min=1.8,
        target_total_odds_max=4.5,
        max_volatility=0.48,
        min_confidence_pct=55.0,
        avoid_minor_leagues=False,
        avoid_volatile_markets=True,
        allow_underdogs=False,
        max_picks_per_league=2,
        preferred_markets=frozenset({"Doble oportunidad", "Total goles", "1X2"}),
        exceptional_odds_min=None,
        max_exceptional_picks=0,
        exceptional_min_ev=0.12,
        exceptional_min_edge_pct=12.0,
        exceptional_max_odds_cap=2.20,
        min_combined_probability=None,
    ),
    "medium": RiskProfile(
        min_picks=3,
        max_picks=5,
        min_prob=0.34,
        min_ev=0.002,
        min_single_odds=1.05,
        max_single_odds=4.0,
        target_total_odds_min=3.0,
        target_total_odds_max=10.0,
        max_volatility=0.65,
        min_confidence_pct=44.0,
        avoid_minor_leagues=False,
        avoid_volatile_markets=False,
        allow_underdogs=False,
        max_picks_per_league=2,
        preferred_markets=frozenset({"Doble oportunidad", "1X2", "Total goles"}),
        exceptional_odds_min=None,
        max_exceptional_picks=0,
        exceptional_min_ev=0.12,
        exceptional_min_edge_pct=12.0,
        exceptional_max_odds_cap=4.0,
        min_combined_probability=None,
    ),
    "high": RiskProfile(
        min_picks=4,
        max_picks=6,
        min_prob=0.30,
        min_ev=0.004,
        min_single_odds=1.06,
        max_single_odds=9.0,
        target_total_odds_min=8.0,
        target_total_odds_max=28.0,
        max_volatility=0.94,
        min_confidence_pct=36.0,
        avoid_minor_leagues=False,
        avoid_volatile_markets=False,
        allow_underdogs=True,
        max_picks_per_league=2,
        preferred_markets=frozenset({"1X2", "Ambos marcan", "Total goles", "Doble oportunidad"}),
        exceptional_odds_min=None,
        max_exceptional_picks=0,
        exceptional_min_ev=0.12,
        exceptional_min_edge_pct=12.0,
        exceptional_max_odds_cap=9.0,
        min_combined_probability=None,
    ),
    "extreme": RiskProfile(
        min_picks=5,
        max_picks=8,
        min_prob=0.28,
        min_ev=0.001,
        min_single_odds=1.06,
        max_single_odds=80.0,
        target_total_odds_min=12.0,
        target_total_odds_max=500.0,
        max_volatility=1.0,
        min_confidence_pct=28.0,
        avoid_minor_leagues=False,
        avoid_volatile_markets=False,
        allow_underdogs=True,
        max_picks_per_league=3,
        preferred_markets=frozenset({"1X2", "Ambos marcan", "Total goles", "Doble oportunidad"}),
        exceptional_odds_min=None,
        max_exceptional_picks=0,
        exceptional_min_ev=0.12,
        exceptional_min_edge_pct=12.0,
        exceptional_max_odds_cap=80.0,
        min_combined_probability=None,
    ),
}


def _volatile_market(c: AccaCandidate) -> bool:
    if c.mercado == "1X2" and c.pick.lower() == "empate":
        return True
    if c.mercado == "Ambos marcan":
        return True
    if c.mercado == "Total goles" and "más" in c.pick.lower():
        return True
    return False


def _is_exceptional_odds_pick(c: AccaCandidate, profile: RiskProfile) -> bool:
    thr = profile.exceptional_odds_min
    if thr is None:
        return False
    return c.metrics.cuota > thr


def _log_pick_reject(c: AccaCandidate, reason: str) -> None:
    logger.info(
        "ACCA_PICK_REJECTED_BY_RISK_PROFILE fixture_id=%s mercado=%s pick=%s cuota=%s prob=%s conf=%s reason=%s",
        c.fixture_id,
        c.mercado,
        c.pick,
        round(c.metrics.cuota, 3),
        round(c.metrics.probabilidad, 4),
        round(c.metrics.confidence_pct, 1),
        reason,
    )


def _passes_odds_bounds(c: AccaCandidate, profile: RiskProfile) -> bool:
    m = c.metrics
    q = m.cuota
    if q < profile.min_single_odds:
        _log_pick_reject(c, "odds_too_low")
        return False
    if q <= profile.max_single_odds:
        return True
    if profile.exceptional_odds_min is not None and q > profile.exceptional_odds_min:
        if q > profile.exceptional_max_odds_cap:
            _log_pick_reject(c, "odds_too_high_exceptional_cap")
            return False
        if m.ev < profile.exceptional_min_ev and m.edge_pct < profile.exceptional_min_edge_pct:
            _log_pick_reject(c, "exceptional_odds_insufficient_edge")
            return False
        return True
    _log_pick_reject(c, "odds_too_high")
    return False


def _first_filter_rejection(c: AccaCandidate, profile: RiskProfile) -> str | None:
    m = c.metrics
    if m.probabilidad < profile.min_prob:
        return "probability_too_low"
    if m.ev < profile.min_ev:
        return "ev_too_low"
    q = m.cuota
    if q < profile.min_single_odds:
        return "odds_too_low"
    if q <= profile.max_single_odds:
        pass
    elif profile.exceptional_odds_min is not None and q > profile.exceptional_odds_min:
        if q > profile.exceptional_max_odds_cap:
            return "odds_too_high_exceptional_cap"
        if m.ev < profile.exceptional_min_ev and m.edge_pct < profile.exceptional_min_edge_pct:
            return "exceptional_odds_insufficient_edge"
    else:
        return "odds_too_high"
    if m.confidence_pct < profile.min_confidence_pct:
        return "confidence_too_low"
    if c.volatility > profile.max_volatility:
        return "volatility_too_high"
    if profile.avoid_minor_leagues and candidate_is_minor(c):
        return "minor_league"
    if profile.avoid_volatile_markets and _volatile_market(c):
        return "volatile_market"
    if not profile.allow_underdogs and m.probabilidad < 0.38 and m.cuota > 3.0:
        return "underdog_extreme"
    if profile.min_confidence_pct >= 65.0 and m.probabilidad < 0.52 and m.cuota > 2.05:
        return "underdog_soft_low_profile"
    if (
        profile.target_total_odds_max <= 5.0
        and not profile.allow_underdogs
        and m.cuota > 1.92
        and m.probabilidad < 0.50
    ):
        return "conservative_underdog_band"
    return None


def _aggregate_reject_stats(candidates: list[AccaCandidate], profile: RiskProfile) -> dict[str, int]:
    stats: dict[str, int] = defaultdict(int)
    for c in candidates:
        r = _first_filter_rejection(c, profile)
        if r is None:
            stats["passed"] += 1
        else:
            stats[r] += 1
    return dict(stats)


def _passes_filters(c: AccaCandidate, profile: RiskProfile) -> bool:
    m = c.metrics
    if m.probabilidad < profile.min_prob:
        _log_pick_reject(c, "probability_too_low")
        return False
    if m.ev < profile.min_ev:
        _log_pick_reject(c, "ev_too_low")
        return False
    if not _passes_odds_bounds(c, profile):
        return False
    if m.confidence_pct < profile.min_confidence_pct:
        _log_pick_reject(c, "confidence_too_low")
        return False
    if c.volatility > profile.max_volatility:
        _log_pick_reject(c, "volatility_too_high")
        return False
    if profile.avoid_minor_leagues and candidate_is_minor(c):
        _log_pick_reject(c, "minor_league")
        return False
    if profile.avoid_volatile_markets and _volatile_market(c):
        _log_pick_reject(c, "volatile_market")
        return False
    if not profile.allow_underdogs and m.probabilidad < 0.38 and m.cuota > 3.0:
        _log_pick_reject(c, "underdog_extreme")
        return False
    if profile.min_confidence_pct >= 65.0 and m.probabilidad < 0.52 and m.cuota > 2.05:
        _log_pick_reject(c, "underdog_soft_low_profile")
        return False
    if (
        profile.target_total_odds_max <= 5.0
        and not profile.allow_underdogs
        and m.cuota > 1.92
        and m.probabilidad < 0.50
    ):
        _log_pick_reject(c, "conservative_underdog_band")
        return False
    return True


def _passes_filters_relaxed_low(c: AccaCandidate) -> bool:
    p = RISK_PROFILES["low"]
    m = c.metrics
    if m.probabilidad < 0.48:
        return False
    if m.ev < 0.001:
        return False
    if not _passes_odds_bounds(c, p):
        return False
    if m.confidence_pct < 47.0:
        return False
    if c.volatility > 0.56:
        return False
    if p.avoid_volatile_markets and _volatile_market(c):
        return False
    if not p.allow_underdogs and m.cuota > 1.92 and m.probabilidad < 0.49:
        return False
    return True


def _passes_filters_relaxed_medium(c: AccaCandidate) -> bool:
    p = RISK_PROFILES["medium"]
    m = c.metrics
    if m.probabilidad < 0.30:
        return False
    if m.ev < 0.0008:
        return False
    if m.cuota < 1.02 or m.cuota > p.max_single_odds:
        return False
    if m.confidence_pct < 38.0:
        return False
    if c.volatility > 0.74:
        return False
    if not p.allow_underdogs and m.probabilidad < 0.33 and m.cuota > 3.3:
        return False
    return True


def _passes_filters_relaxed_high(c: AccaCandidate) -> bool:
    p = RISK_PROFILES["high"]
    m = c.metrics
    if m.probabilidad < 0.26:
        return False
    if m.ev < 0.001:
        return False
    if m.cuota < 1.02 or m.cuota > p.max_single_odds:
        return False
    if m.confidence_pct < 30.0:
        return False
    if c.volatility > 0.99:
        return False
    return True


def _passes_filters_relaxed_extreme(c: AccaCandidate) -> bool:
    p = RISK_PROFILES["extreme"]
    m = c.metrics
    if m.probabilidad < 0.24:
        return False
    if m.ev < 0.0005:
        return False
    if m.cuota < 1.02 or m.cuota > p.max_single_odds:
        return False
    if m.confidence_pct < 24.0:
        return False
    if c.volatility > 1.0:
        return False
    return True


def _pick_score(c: AccaCandidate, profile: RiskProfile) -> float:
    m = c.metrics
    score = m.ev * 55.0 + m.edge_pct * 0.45 + m.confidence_pct * 0.42 + m.probabilidad * 48.0
    if c.mercado in profile.preferred_markets:
        score += 8.0
    if c.odds_source == "bookmaker":
        score += 5.0
    score += c.league_quality * 12.0
    score -= c.volatility * 22.0
    over = max(0.0, m.cuota - profile.max_single_odds)
    score -= over * 22.0
    if profile.exceptional_odds_min and m.cuota > profile.exceptional_odds_min:
        score -= (m.cuota - profile.exceptional_odds_min) * 8.0
    return score


def _band_aware_step_score(
    c: AccaCandidate,
    profile: RiskProfile,
    selected: list[AccaCandidate],
    trial_odds: float,
) -> float:
    m = c.metrics
    n_after = len(selected) + 1
    lo, hi = profile.target_total_odds_min, profile.target_total_odds_max
    target_mid = math.sqrt(max(lo * hi, 1.01))

    score = m.probabilidad * 58.0 + m.ev * 58.0 + m.confidence_pct * 0.36
    score += min(14.0, max(-4.0, m.edge_pct)) * 0.22
    score -= c.volatility * 20.0
    if c.mercado in profile.preferred_markets:
        score += 7.5
    if c.odds_source == "bookmaker":
        score += 4.0
    score += c.league_quality * 9.0

    if trial_odds > hi:
        score -= (trial_odds - hi) * 48.0
    elif n_after >= profile.min_picks and trial_odds < lo:
        score -= (lo - trial_odds) * 14.0
    elif n_after >= profile.min_picks:
        score -= abs(math.log(trial_odds + 1e-9) - math.log(target_mid + 1e-9)) * 5.0

    if hi <= 12.0:
        score -= max(0.0, m.cuota - profile.max_single_odds * 0.85) * 2.8

    return score


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


def _exceptional_count(selected: list[AccaCandidate], profile: RiskProfile) -> int:
    return sum(1 for x in selected if _is_exceptional_odds_pick(x, profile))


def _can_add_pick_exceptional_quota(
    c: AccaCandidate,
    profile: RiskProfile,
    selected: list[AccaCandidate],
) -> bool:
    if not _is_exceptional_odds_pick(c, profile):
        return True
    if _exceptional_count(selected, profile) >= profile.max_exceptional_picks:
        return False
    return True


def _trim_for_min_combined_probability(
    selected: list[AccaCandidate],
    selected_fixture_ids: set[int],
    league_counts: dict[int, int],
    profile: RiskProfile,
) -> None:
    floor = profile.min_combined_probability
    if floor is None or not selected:
        return
    while len(selected) > profile.min_picks and _combined_prob(selected) < floor:
        worst = min(selected, key=lambda x: x.metrics.probabilidad)
        logger.info(
            "ACCA_TRIM_FOR_COMBINED_PROB fixture_id=%s prob=%s combined_was=%s floor=%s",
            worst.fixture_id,
            worst.metrics.probabilidad,
            _combined_prob(selected),
            floor,
        )
        league_counts[worst.league_id] = max(0, league_counts.get(worst.league_id, 0) - 1)
        selected_fixture_ids.discard(worst.fixture_id)
        selected.remove(worst)


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


def _fmt_candidate_line(c: AccaCandidate, rank: int) -> str:
    m = c.metrics
    return (
        f"#{rank} fid={c.fixture_id} lg={c.league_id} {c.mercado}/{c.pick} "
        f"cuota={m.cuota:.3f} p={m.probabilidad:.4f} ev={m.ev:.5f} ev_pct={m.ev_pct:.2f} "
        f"conf={m.confidence_pct:.1f} vol={c.volatility:.3f} src={c.odds_source}"
    )


def _sync_state_from_selected(
    selected: list[AccaCandidate],
) -> tuple[set[int], dict[int, int]]:
    ids: set[int] = set()
    league_counts: dict[int, int] = defaultdict(int)
    for p in selected:
        ids.add(p.fixture_id)
        league_counts[p.league_id] += 1
    return ids, dict(league_counts)


def _clear_and_set_selected(
    selected: list[AccaCandidate],
    selected_fixture_ids: set[int],
    league_counts: dict[int, int],
    new_picks: list[AccaCandidate],
) -> None:
    selected.clear()
    selected_fixture_ids.clear()
    league_counts.clear()
    selected.extend(new_picks)
    ids, lc = _sync_state_from_selected(new_picks)
    selected_fixture_ids.update(ids)
    league_counts.update(lc)


def _assemble_min_odds_under_cap(
    eligible: list[AccaCandidate],
    profile: RiskProfile,
    *,
    cap_multiplier: float = 1.0,
    stage_log: list[str],
) -> list[AccaCandidate]:
    """
    Esqueleto: elige min_picks con fixture distinto, priorizando cuota creciente (producto mínimo),
    respetando cap de cuota combinada = target_max * cap_multiplier.
    """
    cap = profile.target_total_odds_max * cap_multiplier + 1e-6
    pool = sorted(eligible, key=lambda c: (c.metrics.cuota, -c.metrics.probabilidad, -c.metrics.ev))
    out: list[AccaCandidate] = []
    fids: set[int] = set()
    lc: dict[int, int] = defaultdict(int)
    for c in pool:
        if len(out) >= profile.min_picks:
            break
        if c.fixture_id in fids:
            continue
        if lc[c.league_id] >= profile.max_picks_per_league:
            continue
        trial = _combined_odds(out + [c])
        if trial > cap:
            stage_log.append(
                f"ASSEMBLY_SKIP fid={c.fixture_id} cuota={c.metrics.cuota:.3f} trial_total={trial:.3f} cap={cap:.3f}"
            )
            continue
        out.append(c)
        fids.add(c.fixture_id)
        lc[c.league_id] += 1
        stage_log.append(
            f"ASSEMBLY_PICK step={len(out)} fid={c.fixture_id} cuota={c.metrics.cuota:.3f} "
            f"running_total={_combined_odds(out):.3f}"
        )
    return out


def _greedy_enhance_under_cap(
    selected: list[AccaCandidate],
    selected_fixture_ids: set[int],
    league_counts: dict[int, int],
    eligible: list[AccaCandidate],
    profile: RiskProfile,
    *,
    stage_log: list[str],
    skip_counts: dict[str, int],
) -> None:
    """Añade picks hasta max_picks si caben bajo target_max y mejoran score."""
    while len(selected) < profile.max_picks:
        best_c: AccaCandidate | None = None
        best_sc = -1e18
        for c in eligible:
            if c.fixture_id in selected_fixture_ids:
                skip_counts["duplicate_fixture"] = skip_counts.get("duplicate_fixture", 0) + 1
                continue
            if league_counts.get(c.league_id, 0) >= profile.max_picks_per_league:
                skip_counts["league_cap"] = skip_counts.get("league_cap", 0) + 1
                continue
            trial_odds = _combined_odds(selected + [c])
            if trial_odds > profile.target_total_odds_max + 1e-6:
                skip_counts["over_target_total"] = skip_counts.get("over_target_total", 0) + 1
                continue
            if not _can_add_pick_exceptional_quota(c, profile, selected):
                skip_counts["exceptional_quota"] = skip_counts.get("exceptional_quota", 0) + 1
                continue
            sc = _band_aware_step_score(c, profile, selected, trial_odds)
            if sc > best_sc:
                best_sc = sc
                best_c = c
        if best_c is None:
            stage_log.append(f"ENHANCE_STOP no_more_candidates_under_cap at_count={len(selected)}")
            break
        selected.append(best_c)
        selected_fixture_ids.add(best_c.fixture_id)
        league_counts[best_c.league_id] = league_counts.get(best_c.league_id, 0) + 1
        stage_log.append(
            f"ENHANCE_PICK count={len(selected)} fid={best_c.fixture_id} cuota={best_c.metrics.cuota:.3f} "
            f"total={_combined_odds(selected):.3f} score={best_sc:.2f}"
        )


def _shrink_to_max_total_odds_safe(
    selected: list[AccaCandidate],
    selected_fixture_ids: set[int],
    league_counts: dict[int, int],
    profile: RiskProfile,
    *,
    stage_log: list[str],
) -> None:
    """NUNCA baja de min_picks: solo quita picks sobrantes si total > max."""
    before = len(selected)
    while len(selected) > profile.min_picks and _combined_odds(selected) > profile.target_total_odds_max + 1e-6:
        drop = max(selected, key=lambda x: x.metrics.cuota)
        tot = _combined_odds(selected)
        stage_log.append(
            f"SHRINK_REMOVE fid={drop.fixture_id} cuota={drop.metrics.cuota:.3f} "
            f"total_before={tot:.3f} why=total_over_max min_picks_floor={profile.min_picks}"
        )
        lid = drop.league_id
        league_counts[lid] = max(0, league_counts.get(lid, 0) - 1)
        selected_fixture_ids.discard(drop.fixture_id)
        selected.remove(drop)
    stage_log.append(
        f"SHRINK_DONE picks_before={before} picks_after={len(selected)} total={_combined_odds(selected):.3f}"
    )


def _fill_min_picks_within_band(
    selected: list[AccaCandidate],
    selected_fixture_ids: set[int],
    league_counts: dict[int, int],
    eligible: list[AccaCandidate],
    profile: RiskProfile,
    *,
    stage_log: list[str],
    skip_reasons: dict[str, int],
) -> None:
    pool = sorted(eligible, key=lambda c: (c.metrics.cuota, -c.metrics.probabilidad, -c.metrics.ev))
    for c in pool:
        if len(selected) >= profile.min_picks:
            break
        if len(selected) >= profile.max_picks:
            break
        if c.fixture_id in selected_fixture_ids:
            skip_reasons["fill_dup_fixture"] = skip_reasons.get("fill_dup_fixture", 0) + 1
            continue
        if league_counts.get(c.league_id, 0) >= profile.max_picks_per_league:
            skip_reasons["fill_league_cap"] = skip_reasons.get("fill_league_cap", 0) + 1
            continue
        trial_odds = _combined_odds(selected + [c])
        if trial_odds > profile.target_total_odds_max + 1e-6:
            skip_reasons["fill_over_target_total"] = skip_reasons.get("fill_over_target_total", 0) + 1
            continue
        if not _can_add_pick_exceptional_quota(c, profile, selected):
            skip_reasons["fill_exceptional_quota"] = skip_reasons.get("fill_exceptional_quota", 0) + 1
            continue
        selected.append(c)
        selected_fixture_ids.add(c.fixture_id)
        league_counts[c.league_id] = league_counts.get(c.league_id, 0) + 1
        stage_log.append(
            f"FILL_ADD fid={c.fixture_id} cuota={c.metrics.cuota:.3f} count={len(selected)} "
            f"total={_combined_odds(selected):.3f}"
        )


def _hard_guarantee_acca(
    pool: list[AccaCandidate],
    profile: RiskProfile,
    *,
    stage_log: list[str],
) -> list[AccaCandidate]:
    """
    Último recurso: min_picks con fixture distinto, EV>0, cuota válida, sin tope de producto
    (solo sensato si el pool upstream no está vacío).
    """
    usable = [c for c in pool if c.metrics.ev > 0 and c.metrics.cuota >= 1.01 and not math.isnan(c.metrics.cuota)]
    usable.sort(key=lambda c: (c.metrics.cuota, -c.metrics.ev))
    out: list[AccaCandidate] = []
    fids: set[int] = set()
    lc: dict[int, int] = defaultdict(int)
    for c in usable:
        if len(out) >= profile.min_picks:
            break
        if c.fixture_id in fids:
            continue
        if lc[c.league_id] >= profile.max_picks_per_league:
            continue
        out.append(c)
        fids.add(c.fixture_id)
        lc[c.league_id] += 1
        stage_log.append(
            f"HARD_GUARANTEE_PICK step={len(out)} fid={c.fixture_id} cuota={c.metrics.cuota:.3f} "
            f"product={_combined_odds(out):.3f}"
        )
    return out


def _merge_eligible(
    candidates: list[AccaCandidate],
    risk: RiskLevel,
    profile: RiskProfile,
) -> list[AccaCandidate]:
    eligible = [c for c in candidates if _passes_filters(c, profile)]
    seen: set[tuple[int, str, str]] = {(c.fixture_id, c.mercado, c.pick) for c in eligible}

    def add_relaxed(pred: Callable[[AccaCandidate], bool]) -> None:
        nonlocal eligible, seen
        for c in candidates:
            k = (c.fixture_id, c.mercado, c.pick)
            if k in seen:
                continue
            if pred(c):
                eligible.append(c)
                seen.add(k)

    if risk == "low" and len(eligible) < 12:
        add_relaxed(_passes_filters_relaxed_low)
    if risk == "medium" and len(eligible) < 18:
        add_relaxed(_passes_filters_relaxed_medium)
    if risk == "high" and len(eligible) < 24:
        add_relaxed(_passes_filters_relaxed_high)
    if risk == "extreme" and len(eligible) < 30:
        add_relaxed(_passes_filters_relaxed_extreme)

    eligible.sort(key=lambda c: _pick_score(c, profile), reverse=True)
    return eligible


def build_smart_acca(
    candidates: list[AccaCandidate],
    risk: RiskLevel,
    *,
    fixtures_in: int = 0,
) -> dict[str, Any]:
    profile = RISK_PROFILES[risk]
    reject_stats = _aggregate_reject_stats(candidates, profile)
    pipeline_log: list[str] = []
    skip_greedy: dict[str, int] = {}
    fill_skips: dict[str, int] = {}

    logger.info(
        "RISK_PROFILE_START risk=%s min_picks=%s max_picks=%s target_odds=[%s,%s] fixtures_in=%s candidates_total=%s",
        risk,
        profile.min_picks,
        profile.max_picks,
        profile.target_total_odds_min,
        profile.target_total_odds_max,
        fixtures_in,
        len(candidates),
    )

    eligible = _merge_eligible(candidates, risk, profile)
    top_lines = [_fmt_candidate_line(c, i + 1) for i, c in enumerate(eligible[:10])]
    logger.info(
        "ELIGIBLE_STAGE risk=%s eligible_count=%s top10=%s",
        risk,
        len(eligible),
        " | ".join(top_lines) if top_lines else "(none)",
    )

    selected: list[AccaCandidate] = []
    selected_fixture_ids: set[int] = set()
    league_counts: dict[int, int] = defaultdict(int)
    used_fallback = False
    cap_mult = 1.0

    if not eligible and candidates:
        used_fallback = True
        pipeline_log.append("ELIGIBLE_EMPTY using_hard_guarantee_pool_only_ev_positive")
        guaranteed = _hard_guarantee_acca(candidates, profile, stage_log=pipeline_log)
        _clear_and_set_selected(selected, selected_fixture_ids, league_counts, guaranteed)
    elif eligible:
        for mult in (1.0, 1.2, 1.45):
            cap_mult = mult
            assembly_log: list[str] = []
            built = _assemble_min_odds_under_cap(eligible, profile, cap_multiplier=mult, stage_log=assembly_log)
            pipeline_log.extend([f"ASSEMBLY_TRY cap_mult={mult}"] + assembly_log)
            if len(built) >= profile.min_picks:
                _clear_and_set_selected(selected, selected_fixture_ids, league_counts, built)
                if mult > 1.0:
                    used_fallback = True
                    pipeline_log.append(f"ASSEMBLY_USED_SOFT_CAP mult={mult}")
                break
        if len(selected) < profile.min_picks:
            used_fallback = True
            pipeline_log.append("ASSEMBLY_FAILED trying_hard_guarantee_on_eligible_shape")
            hg = _hard_guarantee_acca(eligible, profile, stage_log=pipeline_log)
            if len(hg) >= len(selected):
                _clear_and_set_selected(selected, selected_fixture_ids, league_counts, hg)
    elif candidates:
        used_fallback = True
        pipeline_log.append("ELIGIBLE_EMPTY_AFTER_STRICT_FILTERS hard_guarantee_from_full_pool")
        guaranteed = _hard_guarantee_acca(candidates, profile, stage_log=pipeline_log)
        _clear_and_set_selected(selected, selected_fixture_ids, league_counts, guaranteed)

    logger.info(
        "ASSEMBLY_STAGE risk=%s picks=%s total_odds=%s cap_mult_used=%s log=%s",
        risk,
        len(selected),
        _combined_odds(selected) if selected else 1.0,
        cap_mult,
        " :: ".join(pipeline_log[-12:]) if pipeline_log else "",
    )

    _greedy_enhance_under_cap(
        selected,
        selected_fixture_ids,
        league_counts,
        eligible if eligible else candidates,
        profile,
        stage_log=pipeline_log,
        skip_counts=skip_greedy,
    )
    logger.info(
        "GREEDY_ENHANCE_STAGE risk=%s picks=%s total=%s skip_counts=%s tail=%s",
        risk,
        len(selected),
        _combined_odds(selected) if selected else 1.0,
        skip_greedy,
        " :: ".join([x for x in pipeline_log if x.startswith("ENHANCE_")][-8:]),
    )

    _shrink_to_max_total_odds_safe(
        selected, selected_fixture_ids, league_counts, profile, stage_log=pipeline_log
    )
    logger.info(
        "SHRINK_STAGE_1 risk=%s picks=%s total=%s events=%s",
        risk,
        len(selected),
        _combined_odds(selected) if selected else 1.0,
        " | ".join(x for x in pipeline_log if x.startswith("SHRINK_"))[-2000:],
    )

    _fill_min_picks_within_band(
        selected,
        selected_fixture_ids,
        league_counts,
        eligible if eligible else candidates,
        profile,
        stage_log=pipeline_log,
        skip_reasons=fill_skips,
    )
    logger.info(
        "FILL_STAGE risk=%s picks=%s total=%s skip_reasons=%s events=%s",
        risk,
        len(selected),
        _combined_odds(selected) if selected else 1.0,
        fill_skips,
        " | ".join(x for x in pipeline_log if x.startswith("FILL_"))[-2000:],
    )

    _shrink_to_max_total_odds_safe(
        selected, selected_fixture_ids, league_counts, profile, stage_log=pipeline_log
    )
    logger.info(
        "SHRINK_STAGE_2 risk=%s picks=%s total=%s events=%s",
        risk,
        len(selected),
        _combined_odds(selected) if selected else 1.0,
        " | ".join(x for x in pipeline_log if x.startswith("SHRINK_"))[-2000:],
    )

    if len(selected) < profile.min_picks and candidates:
        used_fallback = True
        pipeline_log.append("POST_FILL_STILL_SHORT hard_guarantee_from_candidates")
        hg2 = _hard_guarantee_acca(candidates, profile, stage_log=pipeline_log)
        if len(hg2) > len(selected):
            _clear_and_set_selected(selected, selected_fixture_ids, league_counts, hg2)

    _trim_for_min_combined_probability(selected, selected_fixture_ids, league_counts, profile)

    if len(selected) < profile.min_picks and candidates:
        used_fallback = True
        pipeline_log.append("POST_TRIM_STILL_SHORT hard_guarantee_final")
        hg3 = _hard_guarantee_acca(candidates, profile, stage_log=pipeline_log)
        if len(hg3) > len(selected):
            _clear_and_set_selected(selected, selected_fixture_ids, league_counts, hg3)

    total_odds = _combined_odds(selected) if selected else 1.0
    combined_p = _combined_prob(selected)
    combined_ev = combined_p * total_odds - 1.0 if selected else 0.0
    conf, risk_score, vol_score = _aggregate_scores(selected)

    logger.info(
        "FINAL_STAGE risk=%s picks=%s total_odds=%s combined_p=%s combined_ev=%s conf=%s "
        "used_budget_fallback=%s fill_skip_reasons=%s pipeline_tail=%s",
        risk,
        len(selected),
        total_odds,
        combined_p,
        round(combined_ev, 5),
        conf,
        used_fallback,
        fill_skips,
        " :: ".join(pipeline_log[-15:]),
    )

    avg_pick_probability = (
        sum(p.metrics.probabilidad for p in selected) / len(selected) if selected else 0.0
    )
    average_pick_odds = sum(p.metrics.cuota for p in selected) / len(selected) if selected else 0.0
    highest_pick_odds = max((p.metrics.cuota for p in selected), default=0.0)
    uniq = {p.fixture_id for p in selected}
    risk_profile_validation: dict[str, Any] = {
        "unique_fixtures_matches_picks": len(uniq) == len(selected),
        "combined_probability": combined_p,
        "combined_probability_floor": profile.min_combined_probability,
        "combined_probability_ok": (
            profile.min_combined_probability is None
            or not selected
            or combined_p >= profile.min_combined_probability
            or len(selected) <= profile.min_picks
        ),
        "exceptional_picks_used": _exceptional_count(selected, profile),
        "max_exceptional_picks": profile.max_exceptional_picks,
        "target_total_odds_min": profile.target_total_odds_min,
        "target_total_odds_max": profile.target_total_odds_max,
        "total_odds_within_target_max": total_odds <= profile.target_total_odds_max + 0.002,
        "total_odds_above_target_min": total_odds + 0.002 >= profile.target_total_odds_min
        or len(selected) < profile.min_picks,
        "fixtures_in_schedule": fixtures_in,
        "filter_reject_stats": reject_stats,
        "min_picks_satisfied": len(selected) >= profile.min_picks,
        "used_budget_fallback": used_fallback,
        "pipeline_log_tail": pipeline_log[-40:],
        "greedy_enhance_skip_counts": skip_greedy,
        "fill_skip_reasons": fill_skips,
    }

    return {
        "risk": risk,
        "risk_label": {
            "low": "Bajo",
            "medium": "Medio",
            "high": "Alto",
            "extreme": "Muy alto",
        }[risk],
        "profile": {
            "min_picks": profile.min_picks,
            "max_picks": profile.max_picks,
            "target_odds_range": f"{profile.target_total_odds_min} – {profile.target_total_odds_max}",
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
        "eligible_count": len(eligible),
        "average_pick_probability": round(avg_pick_probability, 5),
        "average_pick_odds": round(average_pick_odds, 3),
        "highest_pick_odds": round(highest_pick_odds, 3),
        "risk_profile_validation": risk_profile_validation,
    }


def resolve_acca_calendar_day_for_pre_match(
    settings: Settings,
    requested: date,
    *,
    now_utc: datetime | None = None,
    max_extra_days: int = 3,
) -> tuple[date, int, bool]:
    now = now_utc or datetime.now(timezone.utc)
    for offset in range(max_extra_days + 1):
        day = requested + timedelta(days=offset)
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
        if filtered:
            return day, len(filtered), day > requested
    return requested, 0, False


def generate_acca_for_date(
    settings: Settings,
    day: date,
    risk: RiskLevel,
    *,
    fetch_odds: bool = True,
) -> dict[str, Any]:
    payload = fetch_fixtures_by_date_cached(settings, day)
    fixtures = payload.get("response") or []
    if not isinstance(fixtures, list):
        fixtures = []

    logger.info(
        "ACCA_GENERATE fixtures_source=api_football date=%s upstream_count=%s",
        day.isoformat(),
        len(fixtures),
    )

    now_utc = datetime.now(timezone.utc)
    filtered, schedule_discard, filter_meta = filter_and_sort_fixtures_for_acca(
        fixtures,
        now_utc=now_utc,
        min_minutes_before_kickoff=settings.acca_min_minutes_before_kickoff,
    )

    pool = build_acca_candidate_pool(
        filtered,
        settings,
        fetch_odds=fetch_odds,
        max_fixtures=72,
        now_utc=now_utc,
    )
    logger.info(
        "ACCA_GENERATE after_schedule_filter=%s candidate_pool_size=%s",
        len(filtered),
        len(pool),
    )
    built = build_smart_acca(pool, risk, fixtures_in=len(filtered))

    picks_out = []
    for p in built["picks"]:
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
    unique_fixtures_count = len(unique_fids)
    if unique_fixtures_count != len(picks_out):
        logger.warning(
            "ACCA_FIXTURE_UNIQUENESS_MISMATCH pick_count=%s unique_fixtures=%s",
            len(picks_out),
            unique_fixtures_count,
        )

    return {
        "date": day.isoformat(),
        "model_version": "poisson-v1+ev-v1",
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
        "meta": {
            "candidates_pool_size": built["candidates_pool_size"],
            "eligible_after_filters": built["eligible_count"],
            "bookmaker_odds_picks": bookmaker_picks,
            "independence_assumption": "P(combinada) ≈ ∏ P(picks); preparado para correlación/ML.",
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
            "unique_fixtures_count": unique_fixtures_count,
            "average_pick_probability": built.get("average_pick_probability", 0.0),
            "average_pick_odds": built.get("average_pick_odds", 0.0),
            "highest_pick_odds": built.get("highest_pick_odds", 0.0),
            "risk_profile_validation": built.get("risk_profile_validation") or {},
            "persist_status": "not_attempted",
            "persist_error": None,
        },
    }
