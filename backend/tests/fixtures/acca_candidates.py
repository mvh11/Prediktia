"""Factory de AccaCandidate para tests de Smart ACCA."""

from __future__ import annotations

from app.services.acca_candidates import AccaCandidate
from app.services.ev_engine import EvMetrics, compute_ev_metrics


def make_acca_candidate(
    *,
    fixture_id: int,
    cuota: float | None = None,
    probabilidad: float = 0.55,
    mercado: str = "1X2",
    pick: str = "Victoria local",
    league_id: int = 39,
    liga: str = "Premier League (England)",
    country: str = "England",
    equipo_local: str = "Home FC",
    equipo_visitante: str = "Away FC",
    fecha: str = "2026-12-01T18:00:00+00:00",
    odds_source: str = "synthetic",
    market_stability: float = 0.72,
    league_quality: float = 0.95,
) -> AccaCandidate:
    if cuota is None:
        cuota = round(max(1.12, (1.06) / probabilidad), 2)
    metrics = compute_ev_metrics(
        probabilidad,
        cuota,
        market_stability=market_stability,
        league_quality=league_quality,
    )
    if metrics is None:
        metrics = EvMetrics(
            probabilidad=probabilidad,
            cuota=cuota,
            ev=probabilidad * cuota - 1.0,
            ev_pct=(probabilidad * cuota - 1.0) * 100,
            edge_pct=(probabilidad - 1 / cuota) * 100,
            confidence_pct=65.0,
            implied_probability=1 / cuota,
            volatility_hint=0.3,
        )
    return AccaCandidate(
        fixture_id=fixture_id,
        league_id=league_id,
        liga=liga,
        country=country,
        equipo_local=equipo_local,
        equipo_visitante=equipo_visitante,
        fecha=fecha,
        mercado=mercado,
        pick=pick,
        metrics=metrics,
        odds_source=odds_source,  # type: ignore[arg-type]
        market_stability=market_stability,
        league_quality=league_quality,
        volatility=metrics.volatility_hint,
        kickoff_in_minutes=120,
    )


def make_candidate_pool(count: int, *, base_cuota: float = 1.45, base_prob: float = 0.58) -> list[AccaCandidate]:
    """Genera N candidatos con fixture_id único y métricas válidas para ACCA."""
    out: list[AccaCandidate] = []
    for i in range(count):
        prob = min(0.72, base_prob + (i % 5) * 0.02)
        cuota = base_cuota + (i % 7) * 0.08
        out.append(
            make_acca_candidate(
                fixture_id=10_000 + i,
                probabilidad=prob,
                cuota=round(cuota, 2),
                pick=f"Pick {i}",
                mercado="1X2" if i % 2 == 0 else "Doble oportunidad",
            )
        )
    return out


def make_aggressive_pool(count: int) -> list[AccaCandidate]:
    """Candidatos con cuotas altas para perfiles high/extreme."""
    out: list[AccaCandidate] = []
    for i in range(count):
        prob = 0.28 + (i % 4) * 0.03
        cuota = 2.2 + (i % 6) * 0.35
        out.append(
            make_acca_candidate(
                fixture_id=20_000 + i,
                probabilidad=prob,
                cuota=round(cuota, 2),
                pick=f"Aggressive {i}",
            )
        )
    return out
