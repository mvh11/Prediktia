from typing import Any

from pydantic import BaseModel, Field


class LatamDebugTimezone(BaseModel):
    backend_utc_now: str
    query_date_utc: str
    date_param_semantics: str
    fixture_timezone_samples: list[dict[str, Any]]


class LatamDebugUpstream(BaseModel):
    total_fixtures_all_countries: int
    latam_fixtures_found: int
    latam_countries_in_scope: list[str]


class LatamDebugSummary(BaseModel):
    fixtures_found: int
    fixtures_with_odds: int
    fixtures_generating_mock_ev_picks: int
    fixtures_discarded: int
    discard_by_reason: dict[str, int]


class LatamPriorityLeague(BaseModel):
    league_id: int
    label: str
    fixtures_found: int
    fixtures_with_odds: int
    fixtures_generating_mock_ev: int
    sample_odds_messages: list[str] = Field(default_factory=list)


class LatamFixtureTrace(BaseModel):
    country: str
    league_name: str
    league_id: int
    league_id_label: str | None = None
    fixture_id: int
    home: str
    away: str
    fixture_date_iso: str | None = None
    fixture_timezone: str | None = None
    query_date_utc: str
    fixtures: str = "yes"
    parsed: bool
    has_odds: bool
    bookmakers_count: int
    markets_count: int
    mock_picks_count: int
    mock_pick_markets: list[str] = Field(default_factory=list)
    generates_ev_picks: bool
    discard_reason: str | None = None
    odds_message: str | None = None
    odds_fetch_error: str | None = None
    frontend_would_hide_tier_d: bool
    frontend_filter_hints: list[str] = Field(default_factory=list)
    pipeline_ev_source: str
    in_latam_editorial_ids: bool


class LatamDebugResponse(BaseModel):
    timezone: LatamDebugTimezone
    upstream: LatamDebugUpstream
    summary: LatamDebugSummary
    priority_leagues: list[LatamPriorityLeague]
    fixtures: list[LatamFixtureTrace]
    pipeline_notes: dict[str, Any]
