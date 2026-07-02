"""Pruebas del motor Poisson."""

from __future__ import annotations

import math

import pytest

from app.services.poisson import (
    LEAGUE_AVG_GOALS,
    MatchLambdas,
    TeamRatings,
    analyze_fixture_poisson,
    compute_match_lambdas,
    estimate_team_ratings,
    market_probabilities_from_lambdas,
    score_matrix,
)
from tests.fixtures.api_football import make_api_football_fixture


class TestPoissonPmfViaScoreMatrix:
    def test_score_matrix_probabilities_sum_to_one(self):
        lambdas = MatchLambdas(lambda_home=1.4, lambda_away=1.1)
        grid = score_matrix(lambdas, max_goals=6)
        total = sum(sum(row) for row in grid)
        assert math.isclose(total, 1.0, rel_tol=1e-9)

    def test_score_matrix_zero_lambda_home(self):
        lambdas = MatchLambdas(lambda_home=0.0, lambda_away=1.2)
        grid = score_matrix(lambdas, max_goals=3)
        total = sum(sum(row) for row in grid)
        assert math.isclose(total, 1.0, rel_tol=1e-9)
        # Con lambda_home=0 el local casi siempre marca 0 goles.
        assert grid[0][0] > grid[1][0]


class TestEstimateTeamRatings:
    def test_ratings_are_deterministic(self):
        a = estimate_team_ratings("Barcelona", team_id=529, league_id=140, is_home=True)
        b = estimate_team_ratings("Barcelona", team_id=529, league_id=140, is_home=True)
        assert a == b

    def test_home_attack_boost(self):
        home = estimate_team_ratings("Team A", team_id=1, league_id=39, is_home=True)
        away = estimate_team_ratings("Team A", team_id=1, league_id=39, is_home=False)
        assert home.attack >= away.attack

    def test_ratings_within_expected_bounds(self):
        ratings = estimate_team_ratings("X", team_id=99, league_id=0, is_home=False)
        assert 0.55 <= ratings.attack <= 1.45
        assert 0.55 <= ratings.defense <= 1.45
        assert ratings.goals_for_pg > 0
        assert ratings.goals_against_pg > 0


class TestComputeMatchLambdas:
    def test_lambdas_clamped(self):
        strong = TeamRatings(attack=1.45, defense=0.55, goals_for_pg=2.0, goals_against_pg=0.5)
        weak = TeamRatings(attack=0.55, defense=1.45, goals_for_pg=0.5, goals_against_pg=2.0)
        lambdas = compute_match_lambdas(strong, weak)
        assert 0.35 <= lambdas.lambda_home <= 3.8
        assert 0.35 <= lambdas.lambda_away <= 3.8

    def test_home_advantage_increases_home_lambda(self):
        home_rat = estimate_team_ratings("H", team_id=10, league_id=39, is_home=True)
        away_rat = estimate_team_ratings("A", team_id=11, league_id=39, is_home=False)
        lambdas = compute_match_lambdas(home_rat, away_rat)
        baseline_home = LEAGUE_AVG_GOALS * home_rat.attack * away_rat.defense * 1.11
        assert lambdas.lambda_home == round(max(0.35, min(3.8, baseline_home)), 4)


class TestMarketProbabilities:
    def test_probabilities_sum_to_one(self):
        lambdas = MatchLambdas(lambda_home=1.3, lambda_away=1.0)
        probs = market_probabilities_from_lambdas(lambdas)
        assert math.isclose(probs.home_win + probs.draw + probs.away_win, 1.0, rel_tol=1e-4)
        assert math.isclose(probs.over_25 + probs.under_25, 1.0, rel_tol=1e-4)
        assert math.isclose(probs.btts_yes + probs.btts_no, 1.0, rel_tol=1e-4)

    def test_double_chance_coherent_with_1x2(self):
        lambdas = MatchLambdas(lambda_home=1.5, lambda_away=0.9)
        probs = market_probabilities_from_lambdas(lambdas)
        assert math.isclose(probs.double_1x, probs.home_win + probs.draw, rel_tol=1e-4)
        assert math.isclose(probs.double_x2, probs.draw + probs.away_win, rel_tol=1e-4)
        assert math.isclose(probs.double_12, probs.home_win + probs.away_win, rel_tol=1e-4)


class TestAnalyzeFixturePoisson:
    def test_success_with_valid_fixture(self, sample_api_fixture):
        result = analyze_fixture_poisson(sample_api_fixture)
        assert result is not None
        lambdas, probs, home_rat, away_rat = result
        assert lambdas.lambda_home > 0
        assert probs.home_win >= 0

    def test_invalid_input_returns_none(self):
        assert analyze_fixture_poisson(None) is None  # type: ignore[arg-type]
        assert analyze_fixture_poisson("not-a-dict") is None  # type: ignore[arg-type]

    def test_defaults_team_names_when_missing(self):
        item = make_api_football_fixture(home_name="", away_name="")
        item["teams"]["home"]["name"] = None
        item["teams"]["away"]["name"] = None
        result = analyze_fixture_poisson(item)
        assert result is not None
