"""Pruebas del pool de candidatos ACCA."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.acca_candidates import (
    AccaCandidate,
    _is_minor_league,
    _league_quality_score,
    _market_stability,
    _synthetic_odds,
    build_acca_candidate_pool,
)
from tests.fixtures.api_football import make_api_football_fixture
from tests.fixtures.settings import make_test_settings


class TestAccaCandidateHelpers:
    def test_league_quality_tier_s(self):
        assert _league_quality_score(39, "Premier League", "England") >= 0.9

    def test_league_quality_minor_signals(self):
        assert _league_quality_score(0, "U19 League", "England") <= 0.3
        assert _is_minor_league(0, "Women League", "Spain") is True

    @pytest.mark.parametrize(
        "mercado,pick,expected_min",
        [
            ("Doble oportunidad", "1X", 0.85),
            ("1X2", "Victoria local", 0.7),
            ("Ambos marcan", "Sí", 0.5),
        ],
    )
    def test_market_stability(self, mercado, pick, expected_min):
        assert _market_stability(mercado, pick) >= expected_min

    def test_synthetic_odds_minimum(self):
        assert _synthetic_odds(0.5) >= 1.12


class TestBuildAccaCandidatePool:
    def test_builds_from_fixtures_without_odds(self):
        future_ts = int(datetime(2030, 5, 1, 18, 0, tzinfo=timezone.utc).timestamp())
        fixtures = [
            make_api_football_fixture(fixture_id=100 + i, timestamp=future_ts + i * 3600)
            for i in range(5)
        ]
        settings = make_test_settings()
        pool = build_acca_candidate_pool(
            fixtures,
            settings,
            fetch_odds=False,
            max_fixtures=5,
            now_utc=datetime(2030, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
        assert len(pool) > 0
        assert all(isinstance(c, AccaCandidate) for c in pool)
        assert all(c.metrics.ev > -0.09 for c in pool)

    def test_skips_invalid_rows(self):
        pool = build_acca_candidate_pool([{"fixture": {}}], make_test_settings(), fetch_odds=False)
        assert pool == []

    def test_respects_max_fixtures(self):
        future_ts = int(datetime(2030, 5, 1, 18, 0, tzinfo=timezone.utc).timestamp())
        fixtures = [
            make_api_football_fixture(fixture_id=i, timestamp=future_ts + i)
            for i in range(10)
        ]
        pool = build_acca_candidate_pool(
            fixtures,
            make_test_settings(),
            fetch_odds=False,
            max_fixtures=3,
        )
        fixture_ids = {c.fixture_id for c in pool}
        assert len(fixture_ids) <= 3
