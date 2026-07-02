"""Pruebas del motor mock de Value Bets."""

from __future__ import annotations

import pytest

from app.services import value_bets as vb
from app.services.value_bets import build_mock_positive_ev_picks, sort_picks_for_free_tier
from tests.fixtures.api_football import make_api_football_fixture


class TestAssignValueGrade:
    @pytest.mark.parametrize(
        "ev,expected",
        [
            (0.20, "elite"),
            (0.172, "elite"),
            (0.15, "high"),
            (0.108, "high"),
            (0.08, "good"),
            (0.052, "good"),
            (0.03, "risky"),
            (0.0, "risky"),
        ],
    )
    def test_grade_thresholds(self, ev, expected):
        assert vb._assign_value_grade(ev) == expected


class TestCoherentQuote:
    def test_valid_quote_positive_ev(self):
        result = vb._coherent_quote(0.45, 0.08)
        assert result is not None
        cuota, ev = result
        assert cuota >= 1.08
        assert ev >= 0.008
        assert ev <= 0.24
        assert ev == pytest.approx(0.45 * cuota - 1.0, abs=0.02)

    @pytest.mark.parametrize("prob", [0.0, 1.0, -0.1, 1.5])
    def test_invalid_probability_returns_none(self, prob):
        assert vb._coherent_quote(prob, 0.05) is None

    def test_extreme_ev_target_out_of_range(self):
        assert vb._coherent_quote(0.99, 5.0) is None


class TestTripartiteProbs:
    def test_probabilities_sum_to_one(self):
        ph, pd, pa = vb._tripartite_probs("fixture:123")
        assert ph + pd + pa == pytest.approx(1.0, abs=1e-6)

    def test_deterministic_by_seed(self):
        a = vb._tripartite_probs("same-seed")
        b = vb._tripartite_probs("same-seed")
        assert a == b


class TestParseFixtureRow:
    def test_parses_valid_row(self, sample_api_fixture):
        row = vb._parse_fixture_row(sample_api_fixture)
        assert row is not None
        assert row["fixture_id"] == 900001
        assert row["equipo_local"] == "Colo Colo"
        assert "Chile" in row["liga"]

    def test_invalid_rows_return_none(self):
        assert vb._parse_fixture_row(None) is None
        assert vb._parse_fixture_row({}) is None
        assert vb._parse_fixture_row({"fixture": {"id": "x"}}) is None


class TestBuildMockPositiveEvPicks:
    def test_generates_picks_from_fixtures(self):
        fixtures = [
            make_api_football_fixture(fixture_id=1001, league_id=39),
            make_api_football_fixture(fixture_id=1002, league_id=140),
        ]
        picks = build_mock_positive_ev_picks(fixtures)
        assert isinstance(picks, list)
        assert len(picks) > 0
        for pick in picks:
            assert pick["ev"] > 0
            assert pick["cuota"] >= 1.05
            assert 0 < pick["probabilidad"] < 1
            assert pick["value_grade"] in ("elite", "high", "good", "risky")

    def test_empty_fixtures_returns_empty(self):
        assert build_mock_positive_ev_picks([]) == []

    def test_skips_invalid_fixture_rows(self):
        picks = build_mock_positive_ev_picks([{"fixture": {}}])
        assert picks == []

    def test_sorted_by_ev_descending(self):
        fixtures = [make_api_football_fixture(fixture_id=2000 + i, league_id=39) for i in range(5)]
        picks = build_mock_positive_ev_picks(fixtures)
        evs = [p["ev"] for p in picks]
        assert evs == sorted(evs, reverse=True)


class TestSortPicksForFreeTier:
    def test_prioritizes_better_grades(self):
        picks = [
            {"value_grade": "risky", "ev": 0.20, "probabilidad": 0.5},
            {"value_grade": "good", "ev": 0.06, "probabilidad": 0.5},
            {"value_grade": "elite", "ev": 0.18, "probabilidad": 0.5},
        ]
        ordered = sort_picks_for_free_tier(picks)
        assert ordered[0]["value_grade"] == "elite"
        assert ordered[-1]["value_grade"] == "risky"

    def test_same_grade_sorts_by_ev_then_probability(self):
        picks = [
            {"value_grade": "good", "ev": 0.06, "probabilidad": 0.4},
            {"value_grade": "good", "ev": 0.08, "probabilidad": 0.3},
        ]
        ordered = sort_picks_for_free_tier(picks)
        assert ordered[0]["ev"] >= ordered[1]["ev"]

    def test_empty_list(self):
        assert sort_picks_for_free_tier([]) == []
