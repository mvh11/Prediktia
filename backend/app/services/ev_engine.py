"""
EV y métricas de edge a partir de probabilidad del modelo vs cuota.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvMetrics:
    probabilidad: float
    cuota: float
    ev: float
    ev_pct: float
    edge_pct: float
    confidence_pct: float
    implied_probability: float
    volatility_hint: float


def implied_probability(cuota: float) -> float:
    if cuota <= 1.0:
        return 1.0
    return 1.0 / cuota


def compute_ev_metrics(
    probabilidad: float,
    cuota: float,
    *,
    market_stability: float = 0.5,
    league_quality: float = 0.5,
) -> EvMetrics | None:
    """
    EV = (p * cuota) - 1
    edge% ≈ p - implied
  confidence% heurística (lista para ML).
    """
    if probabilidad <= 0 or probabilidad >= 1 or cuota < 1.01:
        return None

    ev = probabilidad * cuota - 1.0
    impl = implied_probability(cuota)
    edge = probabilidad - impl

    # Confianza: probabilidad + estabilidad mercado + calidad liga
    raw_conf = (
        0.52 * probabilidad
        + 0.28 * market_stability
        + 0.20 * league_quality
        + min(0.08, max(-0.08, edge * 0.35))
    )
    confidence_pct = max(0.05, min(0.98, raw_conf)) * 100.0

    # Volatilidad: cuotas altas y probabilidades bajas
    vol = min(
        1.0,
        0.35 * min(1.0, (cuota - 1.0) / 4.0) + 0.45 * (1.0 - probabilidad) + 0.2 * (1.0 - market_stability),
    )

    return EvMetrics(
        probabilidad=round(probabilidad, 5),
        cuota=round(cuota, 3),
        ev=round(ev, 5),
        ev_pct=round(ev * 100.0, 2),
        edge_pct=round(edge * 100.0, 2),
        confidence_pct=round(confidence_pct, 1),
        implied_probability=round(impl, 5),
        volatility_hint=round(vol, 4),
    )
