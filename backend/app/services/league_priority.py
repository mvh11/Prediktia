"""Prioridad de ligas para demo (Tier 1 > Tier 2 > resto)."""

from __future__ import annotations

# API-Football league ids habituales
TIER1_LEAGUE_IDS: frozenset[int] = frozenset(
    {
        39,  # Premier League
        140,  # La Liga
        135,  # Serie A
        78,  # Bundesliga
        61,  # Ligue 1
        2,
        3,  # Champions / Europa
        848,  # Conference
        13,  # Libertadores
        11,  # Sudamericana
        71,  # Brasileirão
        128,  # Argentina LPF
        265,  # Chile Primera
    }
)

TIER2_LEAGUE_IDS: frozenset[int] = frozenset(
    {
        253,  # MLS
        88,  # Eredivisie
        94,  # Portugal
        203,  # Turkey
        40,  # Championship
        144,  # Belgium
        179,  # Scotland
        262,  # Liga MX
        239,  # Colombia
    }
)


def league_priority_score(league_id: int, league_name: str = "", country: str = "") -> float:
    if league_id in TIER1_LEAGUE_IDS:
        return 1.0
    if league_id in TIER2_LEAGUE_IDS:
        return 0.75
    blob = f"{country} {league_name}".lower()
    tier1_names = (
        "premier league",
        "la liga",
        "serie a",
        "bundesliga",
        "ligue 1",
        "champions league",
        "libertadores",
        "brasileir",
        "primera división",
        "liga profesional",
    )
    if any(s in blob for s in tier1_names) and "u21" not in blob and "women" not in blob:
        return 0.92
    tier2_names = ("eredivisie", "primeira liga", "liga portugal", "major league soccer", "championship")
    if any(s in blob for s in tier2_names):
        return 0.7
    return 0.45
