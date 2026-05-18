"""
Pool de candidatos ACCA: Poisson + cuotas (upstream o sintéticas con margen).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from app.config import Settings
from app.services.ev_engine import EvMetrics, compute_ev_metrics
from app.services.league_format import format_league_display
from app.services.league_priority import league_priority_score
from app.services.acca_fixture_filter import kickoff_in_minutes_from_now
from app.services.acca_odds import extract_market_odds
from app.services.football_api import fetch_odds_by_fixture_cached
from app.services.poisson import analyze_fixture_poisson

logger = logging.getLogger(__name__)

OddsSource = Literal["bookmaker", "synthetic"]

# Ligas prioritarias (API-Football ids habituales)
TIER_S_IDS: frozenset[int] = frozenset(
    {39, 140, 135, 78, 61, 71, 265, 128, 262, 239, 2, 3, 13, 11, 848, 253}
)
TIER_A_IDS: frozenset[int] = frozenset({88, 94, 179, 144, 203, 281, 242, 268, 252, 72})
TIER_D_SIGNALS = (
    "women",
    "u17",
    "u18",
    "u19",
    "u20",
    "u21",
    "reserve",
    "reserva",
    "youth",
    "juvenil",
    "amateur",
)


@dataclass
class AccaCandidate:
    fixture_id: int
    league_id: int
    liga: str
    country: str
    equipo_local: str
    equipo_visitante: str
    fecha: str
    mercado: str
    pick: str
    metrics: EvMetrics
    odds_source: OddsSource
    market_stability: float
    league_quality: float
    volatility: float
    kickoff_in_minutes: int | None = None


def _league_quality_score(league_id: int, league_name: str, country: str) -> float:
    if league_id in TIER_S_IDS:
        return 0.95
    if league_id in TIER_A_IDS:
        return 0.78
    blob = f"{country} {league_name}".lower()
    if any(s in blob for s in TIER_D_SIGNALS):
        return 0.25
    return 0.55


def _is_minor_league(league_id: int, league_name: str, country: str) -> bool:
    return _league_quality_score(league_id, league_name, country) < 0.45


def _market_stability(mercado: str, pick: str) -> float:
    p = pick.lower()
    if mercado == "Doble oportunidad":
        return 0.88
    if mercado == "Total goles" and "menos" in p:
        return 0.82
    if mercado == "1X2" and "empate" not in p:
        return 0.72
    if mercado == "Total goles":
        return 0.65
    if mercado == "Ambos marcan":
        return 0.58
    if mercado == "1X2":
        return 0.45
    return 0.5


def _synthetic_odds(prob: float, margin: float = 0.05) -> float:
    """
    Cuota estimada cuando no hay bookmaker.
    Incluye un pequeño edge (~2–4% EV) para poder armar combinadas en demo sin cuotas reales.
    """
    p = max(0.02, min(0.96, prob))
    return round(max(1.12, (1.0 - margin + 0.06) / p), 2)


def _format_liga(name: str, country: str) -> str:
    return format_league_display(name, country)


def _candidates_from_fixture(
    item: dict[str, Any],
    *,
    fetch_odds: bool,
    settings: Settings | None,
    now_utc: datetime | None = None,
) -> list[AccaCandidate]:
    fx = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    fid = fx.get("id")
    if not isinstance(fid, int):
        return []
    fecha = fx.get("date") if isinstance(fx.get("date"), str) else ""
    league = item.get("league") if isinstance(item.get("league"), dict) else {}
    teams = item.get("teams") if isinstance(item.get("teams"), dict) else {}
    home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
    away = teams.get("away") if isinstance(teams.get("away"), dict) else {}

    league_name = (league.get("name") or "—").strip()
    country = (league.get("country") or "").strip()
    league_id = int(league.get("id")) if isinstance(league.get("id"), int) else 0
    h_name = (home.get("name") or "Local").strip()
    a_name = (away.get("name") or "Visitante").strip()

    analyzed = analyze_fixture_poisson(item)
    if not analyzed:
        return []
    _lambdas, probs, _hr, _ar = analyzed

    liga = _format_liga(league_name, country)
    lq = _league_quality_score(league_id, league_name, country)
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    kick_mins = kickoff_in_minutes_from_now(item, now)

    book_odds: dict[str, dict[str, float]] = {}
    if fetch_odds and settings is not None:
        try:
            payload = fetch_odds_by_fixture(settings, fid)
            book_odds = extract_market_odds(payload, h_name, a_name)
        except FootballApiError as exc:
            logger.debug("acca odds skip fixture=%s: %s", fid, exc)

    out: list[AccaCandidate] = []

    def resolve(book: float | None, prob: float) -> tuple[float, OddsSource]:
        if book is not None and book >= 1.01:
            return book, "bookmaker"
        return _synthetic_odds(prob), "synthetic"

    def add(mercado: str, pick: str, prob: float, book_odd: float | None) -> None:
        cuota, source = resolve(book_odd, prob)
        stab = _market_stability(mercado, pick)
        m = compute_ev_metrics(prob, cuota, market_stability=stab, league_quality=lq)
        if m is None:
            return
        if m.ev <= 0 and source == "bookmaker":
            return
        if m.ev <= -0.08:
            return
        out.append(
            AccaCandidate(
                fixture_id=fid,
                league_id=league_id,
                liga=liga,
                country=country,
                equipo_local=h_name,
                equipo_visitante=a_name,
                fecha=fecha,
                mercado=mercado,
                pick=pick,
                metrics=m,
                odds_source=source,
                market_stability=stab,
                league_quality=lq,
                volatility=m.volatility_hint,
                kickoff_in_minutes=kick_mins,
            )
        )

    o1 = book_odds.get("1x2", {})
    oou = book_odds.get("ou_25", {})
    obtts = book_odds.get("btts", {})
    odc = book_odds.get("dc", {})

    add("1X2", "Victoria local", probs.home_win, o1.get("home"))
    add("1X2", "Empate", probs.draw, o1.get("draw"))
    add("1X2", "Victoria visitante", probs.away_win, o1.get("away"))
    add("Total goles", "Más de 2.5", probs.over_25, oou.get("over_25"))
    add("Total goles", "Menos de 2.5", probs.under_25, oou.get("under_25"))
    add("Ambos marcan", "Sí", probs.btts_yes, obtts.get("yes"))
    add("Ambos marcan", "No", probs.btts_no, obtts.get("no"))
    add("Doble oportunidad", "1X", probs.double_1x, odc.get("1x"))
    add("Doble oportunidad", "X2", probs.double_x2, odc.get("x2"))

    return out


def build_acca_candidate_pool(
    fixtures: list[Any],
    settings: Settings | None,
    *,
    fetch_odds: bool = True,
    max_fixtures: int = 40,
    max_odds_fetches: int = 20,
    now_utc: datetime | None = None,
) -> list[AccaCandidate]:
    """
    `fixtures` debe llegar ya filtrado y ordenado (p. ej. por acca_fixture_filter).
    Limita cantidad de fixtures y de peticiones /odds (caché compartida, máx. max_odds_fetches).
    """
    pool: list[AccaCandidate] = []
    n = 0
    odds_used = 0
    for item in fixtures:
        if n >= max_fixtures:
            break
        if not isinstance(item, dict):
            continue
        use_odds = fetch_odds and settings is not None and odds_used < max_odds_fetches
        pool.extend(
            _candidates_from_fixture(
                item,
                fetch_odds=use_odds,
                settings=settings,
                now_utc=now_utc,
            )
        )
        if use_odds:
            odds_used += 1
        n += 1
    logger.info(
        "acca_candidate_pool fixtures_in=%s candidates_out=%s max_fixtures=%s fetch_odds=%s",
        len(fixtures),
        len(pool),
        max_fixtures,
        fetch_odds,
    )
    return pool


def candidate_is_minor(c: AccaCandidate) -> bool:
    return _is_minor_league(c.league_id, c.liga, c.country)
