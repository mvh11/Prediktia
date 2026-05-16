"""
Trazado del pipeline fixtures → odds (upstream) → picks EV mock → filtros (referencia).

Solo para diagnóstico; no altera /value-bets ni la UI.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from app.config import Settings
from app.services.football_api import FootballApiError, fetch_odds_by_fixture
from app.services.value_bets import (
    LATAM_EDITORIAL_IDS,
    _parse_fixture_row,
    build_mock_positive_ev_picks,
)

logger = logging.getLogger(__name__)

# Países LATAM del endpoint /debug/latam
LATAM_COUNTRY_NAMES: frozenset[str] = frozenset(
    {
        "chile",
        "brazil",
        "brasil",
        "argentina",
        "uruguay",
        "peru",
        "perú",
        "colombia",
        "ecuador",
        "paraguay",
        "bolivia",
        "venezuela",
        "mexico",
        "méxico",
    }
)

PRIORITY_LEAGUE_IDS: dict[int, str] = {
    265: "Campeonato Nacional / Primera División (Chile)",
    71: "Brasileirão Serie A",
    72: "Brasileirão Serie B",
    13: "Copa Libertadores",
    11: "Copa Sudamericana",
    128: "Argentina Liga Profesional",
    268: "Uruguay Primera",
    281: "Perú Liga 1",
    239: "Colombia Primera A",
    242: "Ecuador LigaPro",
    252: "Paraguay Primera",
    262: "Liga MX",
}

# Señales tier D (alineadas con frontend leagueTiers — aproximación backend)
_TIER_D_SUBSTRINGS = (
    "women",
    "womens",
    "femenin",
    "femenina",
    "ladies",
    "u17",
    "u18",
    "u19",
    "u20",
    "u21",
    "u22",
    "u23",
    "sub-17",
    "sub-19",
    "sub-21",
    "juvenil",
    "youth",
    "academy",
    "reserva",
    "reserve",
    "b team",
    "regional",
    "amateur",
    "tercera",
    "segunda b",
    "liga iii",
    "district",
)


def _fold(s: str) -> str:
    return s.lower().strip()


def is_latam_country(country: str) -> bool:
    c = _fold(country)
    if not c:
        return False
    if c in LATAM_COUNTRY_NAMES:
        return True
    return any(c == n or c.startswith(n + " ") for n in LATAM_COUNTRY_NAMES)


def _tier_d_hint(base: dict[str, Any]) -> bool:
    blob = _fold(
        f"{base.get('country', '')} {base.get('league_name', '')} {base.get('liga', '')}"
    )
    return any(sig in blob for sig in _TIER_D_SUBSTRINGS)


def _count_odds_stats(odds_payload: dict[str, Any]) -> tuple[int, int, str | None]:
    """
    Devuelve (bookmakers, markets, odds_message).
    """
    response = odds_payload.get("response")
    if not isinstance(response, list) or len(response) == 0:
        errors = odds_payload.get("errors")
        if errors:
            return 0, 0, f"odds API errors: {errors}"
        return 0, 0, "odds unavailable for this league/plan/provider (empty response)"

    bookmakers = 0
    markets = 0
    for block in response:
        if not isinstance(block, dict):
            continue
        bms = block.get("bookmakers")
        if not isinstance(bms, list):
            continue
        bookmakers += len(bms)
        for bm in bms:
            if not isinstance(bm, dict):
                continue
            bets = bm.get("bets")
            if isinstance(bets, list):
                markets += len(bets)

    if bookmakers == 0:
        return 0, 0, "odds unavailable for this league/plan/provider (no bookmakers)"

    return bookmakers, markets, None


def _mock_picks_for_fixture(item: dict[str, Any]) -> list[dict[str, Any]]:
    return build_mock_positive_ev_picks([item])


def _primary_discard_reason(
    *,
    parsed: bool,
    mock_picks_count: int,
    in_fixtures: bool,
) -> str | None:
    """Motivo por el que el fixture no genera filas en GET /value-bets (pipeline mock)."""
    if not in_fixtures:
        return "not_in_fixtures_for_date"
    if not parsed:
        return "invalid_fixture_row"
    if mock_picks_count == 0:
        return "mock_no_ev_lines"
    return None


def _log_fixture_trace(trace: dict[str, Any]) -> None:
    country = trace.get("country") or "?"
    home = trace.get("home") or "—"
    away = trace.get("away") or "—"
    logger.info(
        "[%s] %s vs %s\n"
        "fixtures=%s\n"
        "parsed=%s\n"
        "odds=%s\n"
        "bookmakers=%s\n"
        "markets=%s\n"
        "mock_picks=%s\n"
        "generates_ev_picks=%s\n"
        "discard_reason=%s\n"
        "odds_note=%s\n"
        "frontend_tier_d_hide=%s",
        country,
        home,
        away,
        "yes" if trace.get("fixtures") == "yes" else "no",
        "yes" if trace.get("parsed") else "no",
        "yes" if trace.get("has_odds") else "no",
        trace.get("bookmakers_count", 0),
        trace.get("markets_count", 0),
        trace.get("mock_picks_count", 0),
        "yes" if trace.get("generates_ev_picks") else "no",
        trace.get("discard_reason") or "ok",
        trace.get("odds_message") or "—",
        "yes" if trace.get("frontend_would_hide_tier_d") else "no",
    )


def trace_fixture(
    item: dict[str, Any],
    settings: Settings,
    *,
    fetch_odds: bool,
    query_date_utc: date,
) -> dict[str, Any]:
    league = item.get("league") if isinstance(item.get("league"), dict) else {}
    teams = item.get("teams") if isinstance(item.get("teams"), dict) else {}
    fx = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
    away = teams.get("away") if isinstance(teams.get("away"), dict) else {}

    country = (league.get("country") or "").strip() if isinstance(league.get("country"), str) else ""
    league_name = (league.get("name") or "").strip() if isinstance(league.get("name"), str) else ""
    league_id = int(league.get("id")) if isinstance(league.get("id"), int) else 0
    fixture_id = int(fx.get("id")) if isinstance(fx.get("id"), int) else 0
    fixture_date = fx.get("date") if isinstance(fx.get("date"), str) else None
    fixture_tz = fx.get("timezone") if isinstance(fx.get("timezone"), str) else None

    base = _parse_fixture_row(item)
    parsed = base is not None

    has_odds = False
    bookmakers_count = 0
    markets_count = 0
    odds_message: str | None = None
    odds_fetch_error: str | None = None

    if fetch_odds and fixture_id > 0:
        try:
            odds_payload = fetch_odds_by_fixture(settings, fixture_id)
            bookmakers_count, markets_count, odds_message = _count_odds_stats(odds_payload)
            has_odds = bookmakers_count > 0
        except FootballApiError as exc:
            odds_fetch_error = str(exc)
            odds_message = "odds unavailable for this league/plan/provider (API error)"
            has_odds = False

    mock_picks: list[dict[str, Any]] = []
    if parsed:
        mock_picks = _mock_picks_for_fixture(item)

    mock_picks_count = len(mock_picks)
    generates_ev = mock_picks_count > 0

    frontend_tier_d = _tier_d_hint(base) if base else _tier_d_hint(
        {
            "country": country,
            "league_name": league_name,
            "liga": league_name,
        }
    )

    discard = _primary_discard_reason(
        parsed=parsed,
        mock_picks_count=mock_picks_count,
        in_fixtures=True,
    )

    # Filtros que solo aplican en frontend (informativos)
    frontend_filters: list[str] = []
    if frontend_tier_d:
        frontend_filters.append("tier_d_hidden_by_default")
    if base:
        ev_max = max((p["ev"] for p in mock_picks), default=0.0)
        if ev_max < 0.052:
            frontend_filters.append("low_ev_grade_risky_only")
    if not generates_ev:
        frontend_filters.append("no_picks_in_value_bets_response")

    trace = {
        "country": country or "—",
        "league_name": league_name,
        "league_id": league_id,
        "league_id_label": PRIORITY_LEAGUE_IDS.get(league_id),
        "fixture_id": fixture_id,
        "home": (home.get("name") if isinstance(home.get("name"), str) else None) or "—",
        "away": (away.get("name") if isinstance(away.get("name"), str) else None) or "—",
        "fixture_date_iso": fixture_date,
        "fixture_timezone": fixture_tz,
        "query_date_utc": query_date_utc.isoformat(),
        "fixtures": "yes",
        "parsed": parsed,
        "has_odds": has_odds,
        "bookmakers_count": bookmakers_count,
        "markets_count": markets_count,
        "mock_picks_count": mock_picks_count,
        "mock_pick_markets": [p.get("mercado") for p in mock_picks],
        "generates_ev_picks": generates_ev,
        "discard_reason": discard,
        "odds_message": odds_message,
        "odds_fetch_error": odds_fetch_error,
        "frontend_would_hide_tier_d": frontend_tier_d,
        "frontend_filter_hints": frontend_filters,
        "pipeline_ev_source": "mock_deterministic (value_bets no consume odds upstream hoy)",
        "in_latam_editorial_ids": league_id in LATAM_EDITORIAL_IDS,
    }
    _log_fixture_trace(trace)
    return trace


def build_latam_debug_report(
    settings: Settings,
    day: date,
    *,
    fetch_odds: bool = True,
) -> dict[str, Any]:
    from app.services.football_api import fetch_fixtures_by_date_cached

    now_utc = datetime.now(timezone.utc)
    payload = fetch_fixtures_by_date_cached(settings, day)
    all_fixtures = payload.get("response") or []
    if not isinstance(all_fixtures, list):
        all_fixtures = []

    latam_items: list[dict[str, Any]] = []
    for item in all_fixtures:
        if not isinstance(item, dict):
            continue
        league = item.get("league") if isinstance(item.get("league"), dict) else {}
        country = league.get("country") if isinstance(league.get("country"), str) else ""
        if is_latam_country(country):
            latam_items.append(item)

    traces: list[dict[str, Any]] = []
    for item in latam_items:
        traces.append(
            trace_fixture(item, settings, fetch_odds=fetch_odds, query_date_utc=day)
        )

    with_odds = sum(1 for t in traces if t["has_odds"])
    generates = sum(1 for t in traces if t["generates_ev_picks"])
    discarded = [t for t in traces if t.get("discard_reason")]

    by_reason: dict[str, int] = {}
    for t in discarded:
        r = t.get("discard_reason") or "unknown"
        by_reason[r] = by_reason.get(r, 0) + 1

    priority_leagues: list[dict[str, Any]] = []
    for lid, label in PRIORITY_LEAGUE_IDS.items():
        league_traces = [t for t in traces if t.get("league_id") == lid]
        priority_leagues.append(
            {
                "league_id": lid,
                "label": label,
                "fixtures_found": len(league_traces),
                "fixtures_with_odds": sum(1 for t in league_traces if t["has_odds"]),
                "fixtures_generating_mock_ev": sum(
                    1 for t in league_traces if t["generates_ev_picks"]
                ),
                "sample_odds_messages": list(
                    {
                        t["odds_message"]
                        for t in league_traces
                        if t.get("odds_message")
                    }
                )[:3],
            }
        )

    tz_samples = [
        {
            "fixture_id": t["fixture_id"],
            "date_iso": t["fixture_date_iso"],
            "timezone": t["fixture_timezone"],
            "country": t["country"],
        }
        for t in traces[:15]
    ]

    return {
        "timezone": {
            "backend_utc_now": now_utc.isoformat(),
            "query_date_utc": day.isoformat(),
            "date_param_semantics": (
                "GET /fixtures?date=YYYY-MM-DD usa el día calendario UTC (igual que /matches y /value-bets). "
                "Partidos nocturnos LATAM pueden caer en el día UTC anterior/siguiente."
            ),
            "fixture_timezone_samples": tz_samples,
        },
        "upstream": {
            "total_fixtures_all_countries": len(all_fixtures),
            "latam_fixtures_found": len(latam_items),
            "latam_countries_in_scope": sorted(LATAM_COUNTRY_NAMES),
        },
        "summary": {
            "fixtures_found": len(traces),
            "fixtures_with_odds": with_odds,
            "fixtures_generating_mock_ev_picks": generates,
            "fixtures_discarded": len(discarded),
            "discard_by_reason": by_reason,
        },
        "priority_leagues": priority_leagues,
        "fixtures": traces,
        "pipeline_notes": {
            "fixtures_source": "API-Football GET /fixtures?date=",
            "odds_source": "API-Football GET /odds?fixture= (solo en este debug; no usado en /value-bets)",
            "ev_picks_source": "mock en app.services.value_bets (sin odds reales)",
            "frontend_filters_not_in_backend": [
                "tier D oculto por defecto (heurística frontend_would_hide_tier_d)",
                "cancelados/postergados ocultos",
                "orden editorial (región/prestigio/score)",
                "filtro por liga seleccionada",
                "paginación visibleCount +20",
            ],
            "bookmakers_insufficient": (
                "No aplica en backend actual: no hay umbral de bookmakers en mock EV."
            ),
        },
    }


def log_all_fixtures_pipeline(
    fixtures: list[Any],
    settings: Settings,
    day: date,
    *,
    fetch_odds: bool = False,
    latam_only: bool = True,
) -> None:
    """Log detallado por fixture (opcional desde /value-bets si se activa)."""
    for item in fixtures:
        if not isinstance(item, dict):
            continue
        league = item.get("league") if isinstance(item.get("league"), dict) else {}
        country = league.get("country") if isinstance(league.get("country"), str) else ""
        if latam_only and not is_latam_country(country):
            continue
        trace_fixture(item, settings, fetch_odds=fetch_odds, query_date_utc=day)
