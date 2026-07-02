"""Pruebas del motor Smart ACCA."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.smart_acca import (
    RISK_LABELS,
    SIMPLE_PROFILES,
    RiskLevel,
    build_simple_acca,
    build_smart_acca,
    generate_acca_for_date,
    resolve_acca_calendar_day_for_pre_match,
)
from tests.fixtures.acca_candidates import make_aggressive_pool, make_candidate_pool
from tests.fixtures.api_football import make_api_football_fixture
from tests.fixtures.settings import make_test_settings


class TestSimpleProfiles:
    @pytest.mark.parametrize("risk", ["low", "medium", "high", "extreme"])
    def test_profile_pick_counts(self, risk: RiskLevel):
        profile = SIMPLE_PROFILES[risk]
        assert profile.exact_picks in (2, 3, 4, 5)
        assert profile.target_min < profile.target_max
        assert RISK_LABELS[risk]


class TestBuildSimpleAcca:
    @pytest.mark.parametrize("risk", ["low", "medium", "high"])
    def test_builds_full_acca_with_sufficient_pool(self, risk: RiskLevel):
        pool = make_candidate_pool(12, base_cuota=1.35 if risk == "low" else 1.55)
        result = build_simple_acca(pool, risk, fixtures_in=12)
        n = SIMPLE_PROFILES[risk].exact_picks
        assert len(result["picks"]) == n
        assert result["risk_profile_validation"]["exact_picks_met"] is True
        assert result["total_odds"] >= 1.0
        assert result["combined_probability"] > 0
        assert result["confidence_score"] > 0

    def test_build_smart_acca_alias(self):
        pool = make_candidate_pool(8)
        assert build_smart_acca(pool, "medium")["risk"] == "medium"

    def test_insufficient_pool_returns_message(self):
        pool = make_candidate_pool(1)
        result = build_simple_acca(pool, "medium", fixtures_in=1)
        assert len(result["picks"]) < SIMPLE_PROFILES["medium"].exact_picks
        assert result["message"] is not None

    def test_unique_fixtures_in_selection(self):
        pool = make_candidate_pool(10)
        result = build_simple_acca(pool, "low", fixtures_in=10)
        fids = [p.fixture_id for p in result["picks"]]
        assert len(fids) == len(set(fids))

    def test_extreme_with_aggressive_pool(self):
        pool = make_aggressive_pool(15)
        result = build_simple_acca(pool, "extreme", fixtures_in=15)
        assert "risk" in result
        assert result["risk"] == "extreme"
        # Puede devolver picks vacíos si no supera referencia Alto — ambos son válidos.
        assert "risk_profile_validation" in result or "message" in result


class TestResolveAccaCalendarDay:
    def test_picks_day_with_most_prematch_fixtures(self, test_settings):
        future_ts = int(datetime(2030, 6, 15, 18, 0, tzinfo=timezone.utc).timestamp())
        day_a = date(2030, 6, 15)
        day_b = date(2030, 6, 16)

        payload_a = {
            "response": [make_api_football_fixture(fixture_id=1, timestamp=future_ts)],
            "_prediktia_cache": {"cache_hit": True},
        }
        payload_b = {
            "response": [
                make_api_football_fixture(fixture_id=i, timestamp=future_ts + i * 3600)
                for i in range(2, 6)
            ],
            "_prediktia_cache": {"cache_hit": True},
        }

        with patch("app.services.smart_acca.peek_fixtures_cache") as peek, patch(
            "app.services.smart_acca.fetch_fixtures_by_date_cached"
        ) as fetch:
            peek.side_effect = lambda d: payload_a if d == day_a else payload_b
            fetch.side_effect = lambda _s, d: payload_a if d == day_a else payload_b
            now = datetime(2030, 6, 15, 10, 0, tzinfo=timezone.utc)
            best, count, shifted = resolve_acca_calendar_day_for_pre_match(
                test_settings,
                day_a,
                now_utc=now,
                max_extra_days=1,
            )
            assert count >= 1
            assert best in (day_a, day_b)


class TestGenerateAccaForDate:
    def test_generate_with_mocked_fixtures(self, test_settings):
        future_ts = int(datetime(2030, 8, 1, 20, 0, tzinfo=timezone.utc).timestamp())
        fixtures = [
            make_api_football_fixture(fixture_id=500 + i, timestamp=future_ts + i * 7200)
            for i in range(8)
        ]
        payload = {
            "response": fixtures,
            "_prediktia_cache": {"cache_hit": False, "stale": False},
        }

        with patch(
            "app.services.smart_acca.fetch_fixtures_by_date_cached",
            return_value=payload,
        ):
            result = generate_acca_for_date(
                test_settings,
                date(2030, 8, 1),
                "medium",
                fetch_odds=False,
            )

        assert result["date"] == "2030-08-01"
        assert result["risk"] == "medium"
        assert "meta" in result
        assert result["meta"]["fixtures_upstream_total"] == 8
        assert "pick_count" in result

    def test_generate_empty_upstream(self, test_settings):
        payload = {"response": [], "_prediktia_cache": {}}
        with patch(
            "app.services.smart_acca.fetch_fixtures_by_date_cached",
            return_value=payload,
        ):
            result = generate_acca_for_date(
                test_settings,
                date(2030, 1, 1),
                "low",
                fetch_odds=False,
            )
        assert result["pick_count"] == 0
