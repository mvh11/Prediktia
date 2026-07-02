"""Pruebas de prioridad de ligas."""

from __future__ import annotations

import pytest

from app.services.league_priority import league_priority_score


class TestLeaguePriorityScore:
    def test_tier1_by_id(self):
        assert league_priority_score(39) == 1.0
        assert league_priority_score(265) == 1.0

    def test_tier2_by_id(self):
        assert league_priority_score(253) == 0.75

    def test_tier1_by_name_heuristic(self):
        score = league_priority_score(0, "Premier League", "England")
        assert score >= 0.9

    def test_women_league_not_boosted_by_name(self):
        score = league_priority_score(0, "Premier League Women", "England")
        assert score < 0.92

    def test_unknown_league_default(self):
        assert league_priority_score(99999, "Regional Cup", "Nowhere") == 0.45

    @pytest.mark.parametrize("league_id", [88, 94])
    def test_tier2_ids(self, league_id):
        assert league_priority_score(league_id) == 0.75
