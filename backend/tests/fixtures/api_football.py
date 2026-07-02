"""Constructores de fixtures API-Football para tests (sin llamadas HTTP)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def make_api_football_fixture(
    *,
    fixture_id: int = 1,
    league_id: int = 39,
    league_name: str = "Premier League",
    country: str = "England",
    home_name: str = "Arsenal",
    away_name: str = "Chelsea",
    home_id: int = 42,
    away_id: int = 49,
    status_short: str = "NS",
    status_long: str = "Not Started",
    date_iso: str | None = None,
    timestamp: int | None = None,
) -> dict[str, Any]:
    kickoff = date_iso or datetime(2026, 6, 1, 18, 0, tzinfo=timezone.utc).isoformat()
    fx: dict[str, Any] = {
        "id": fixture_id,
        "date": kickoff,
        "status": {"short": status_short, "long": status_long, "elapsed": None},
    }
    if timestamp is not None:
        fx["timestamp"] = timestamp

    return {
        "fixture": fx,
        "league": {"id": league_id, "name": league_name, "country": country},
        "teams": {
            "home": {"id": home_id, "name": home_name},
            "away": {"id": away_id, "name": away_name},
        },
    }
