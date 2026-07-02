"""Pruebas del motor EV."""

from __future__ import annotations

import pytest

from app.services.ev_engine import compute_ev_metrics, implied_probability


class TestImpliedProbability:
    def test_fair_odds(self):
        assert implied_probability(2.0) == pytest.approx(0.5)

    def test_invalid_odds_returns_one(self):
        assert implied_probability(1.0) == 1.0
        assert implied_probability(0.5) == 1.0

    def test_high_odds_low_implied(self):
        assert implied_probability(10.0) == pytest.approx(0.1)


class TestComputeEvMetrics:
    def test_positive_ev_when_model_beats_market(self):
        metrics = compute_ev_metrics(0.55, 2.10)
        assert metrics is not None
        assert metrics.ev == pytest.approx(0.55 * 2.10 - 1.0, rel=1e-4)
        assert metrics.ev_pct == pytest.approx(metrics.ev * 100, rel=1e-4)
        assert metrics.edge_pct > 0
        assert 5.0 <= metrics.confidence_pct <= 98.0
        assert 0.0 <= metrics.volatility_hint <= 1.0

    def test_zero_ev_at_fair_line(self):
        metrics = compute_ev_metrics(0.5, 2.0)
        assert metrics is not None
        assert metrics.ev == pytest.approx(0.0, abs=1e-4)
        assert metrics.edge_pct == pytest.approx(0.0, abs=1e-2)

    @pytest.mark.parametrize(
        "prob,cuota",
        [
            (0.0, 2.0),
            (1.0, 2.0),
            (-0.1, 2.0),
            (0.5, 1.0),
            (0.5, 0.9),
        ],
    )
    def test_invalid_inputs_return_none(self, prob, cuota):
        assert compute_ev_metrics(prob, cuota) is None

    def test_stability_and_league_quality_affect_confidence(self):
        low = compute_ev_metrics(0.45, 2.2, market_stability=0.2, league_quality=0.2)
        high = compute_ev_metrics(0.45, 2.2, market_stability=0.9, league_quality=0.9)
        assert low is not None and high is not None
        assert high.confidence_pct > low.confidence_pct

    def test_high_odds_increase_volatility_hint(self):
        low_odds = compute_ev_metrics(0.6, 1.8)
        high_odds = compute_ev_metrics(0.25, 5.0)
        assert low_odds is not None and high_odds is not None
        assert high_odds.volatility_hint > low_odds.volatility_hint
