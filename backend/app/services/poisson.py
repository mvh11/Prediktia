"""
Motor Poisson para probabilidades de mercado (1X2, O/U, BTTS, doble oportunidad).

Diseñado para sustituir ratings mock por estadísticas reales / ML sin cambiar la API.
"""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass
from typing import Any

# Media de goles por equipo y partido (referencia top leagues).
LEAGUE_AVG_GOALS = 1.32
HOME_ADVANTAGE = 1.11
MAX_GOALS_GRID = 8


@dataclass(frozen=True)
class TeamRatings:
    """Ratings relativos 0.55–1.45 (ataque ofensivo, defensa = factor de goles encajados)."""

    attack: float
    defense: float
    goals_for_pg: float
    goals_against_pg: float


@dataclass(frozen=True)
class MatchLambdas:
    lambda_home: float
    lambda_away: float


@dataclass(frozen=True)
class MarketProbabilities:
    home_win: float
    draw: float
    away_win: float
    over_25: float
    under_25: float
    btts_yes: float
    btts_no: float
    double_1x: float
    double_x2: float
    double_12: float


def _u01(seed: str) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return struct.unpack(">I", digest[:4])[0] / 2**32


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def estimate_team_ratings(
    team_name: str,
    *,
    team_id: int = 0,
    league_id: int = 0,
    is_home: bool,
) -> TeamRatings:
    """
    Ratings simplificados (deterministas) hasta conectar histórico API / ML.

    Combina hash estable + sesgo localía en ataque.
    """
    seed = f"prediktia:ratings:{league_id}:{team_id}:{team_name.strip().lower()}"
    atk = 0.72 + _u01(seed + ":atk") * 0.58
    dfn = 0.72 + _u01(seed + ":dfn") * 0.58
    if is_home:
        atk *= 1.04
    gf = LEAGUE_AVG_GOALS * atk
    ga = LEAGUE_AVG_GOALS * dfn
    return TeamRatings(
        attack=round(atk, 4),
        defense=round(dfn, 4),
        goals_for_pg=round(gf, 3),
        goals_against_pg=round(ga, 3),
    )


def compute_match_lambdas(home: TeamRatings, away: TeamRatings) -> MatchLambdas:
    """xG esperados local/visitante desde fuerza ofensiva/defensiva."""
    lam_h = LEAGUE_AVG_GOALS * home.attack * away.defense * HOME_ADVANTAGE
    lam_a = LEAGUE_AVG_GOALS * away.attack * home.defense
    lam_h = max(0.35, min(3.8, lam_h))
    lam_a = max(0.35, min(3.8, lam_a))
    return MatchLambdas(lambda_home=round(lam_h, 4), lambda_away=round(lam_a, 4))


def score_matrix(lambdas: MatchLambdas, max_goals: int = MAX_GOALS_GRID) -> list[list[float]]:
    """Matriz P(home=i, away=j) asumiendo independencia Poisson."""
    ph = [_poisson_pmf(i, lambdas.lambda_home) for i in range(max_goals + 1)]
    pa = [_poisson_pmf(j, lambdas.lambda_away) for j in range(max_goals + 1)]
    grid = [[ph[i] * pa[j] for j in range(max_goals + 1)] for i in range(max_goals + 1)]
    total = sum(sum(row) for row in grid)
    if total <= 0:
        return grid
    return [[x / total for x in row] for row in grid]


def market_probabilities_from_lambdas(lambdas: MatchLambdas) -> MarketProbabilities:
    grid = score_matrix(lambdas)
    n = len(grid) - 1
    home_win = draw = away_win = 0.0
    over_25 = under_25 = 0.0
    btts_yes = btts_no = 0.0

    for i in range(n + 1):
        for j in range(n + 1):
            p = grid[i][j]
            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p
            if i + j >= 3:
                over_25 += p
            else:
                under_25 += p
            if i >= 1 and j >= 1:
                btts_yes += p
            else:
                btts_no += p

    return MarketProbabilities(
        home_win=round(home_win, 5),
        draw=round(draw, 5),
        away_win=round(away_win, 5),
        over_25=round(over_25, 5),
        under_25=round(under_25, 5),
        btts_yes=round(btts_yes, 5),
        btts_no=round(btts_no, 5),
        double_1x=round(home_win + draw, 5),
        double_x2=round(draw + away_win, 5),
        double_12=round(home_win + away_win, 5),
    )


def analyze_fixture_poisson(
  item: dict[str, Any],
) -> tuple[MatchLambdas, MarketProbabilities, TeamRatings, TeamRatings] | None:
    """A partir de fila API-Football /fixtures."""
    if not isinstance(item, dict):
        return None
    teams = item.get("teams") if isinstance(item.get("teams"), dict) else {}
    league = item.get("league") if isinstance(item.get("league"), dict) else {}
    home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
    away = teams.get("away") if isinstance(teams.get("away"), dict) else {}

    h_name = (home.get("name") or "").strip() or "Local"
    a_name = (away.get("name") or "").strip() or "Visitante"
    h_id = int(home.get("id")) if isinstance(home.get("id"), int) else 0
    a_id = int(away.get("id")) if isinstance(away.get("id"), int) else 0
    lid = int(league.get("id")) if isinstance(league.get("id"), int) else 0

    h_rat = estimate_team_ratings(h_name, team_id=h_id, league_id=lid, is_home=True)
    a_rat = estimate_team_ratings(a_name, team_id=a_id, league_id=lid, is_home=False)
    lambdas = compute_match_lambdas(h_rat, a_rat)
    probs = market_probabilities_from_lambdas(lambdas)
    return lambdas, probs, h_rat, a_rat
