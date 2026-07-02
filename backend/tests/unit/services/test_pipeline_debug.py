"""Pruebas del pipeline de debug LATAM (sin API-Football real)."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from app.services import pipeline_debug as pd
from app.services.football_api import FootballApiError
from tests.fixtures.api_football import make_api_football_fixture
from tests.fixtures.settings import make_test_settings


class TestLatamHelpers:
    @pytest.mark.parametrize(
        "country,expected",
        [
            ("Chile", True),
            ("Brazil", True),
            ("Brasil", True),
            ("Argentina", True),
            ("England", False),
            ("", False),
        ],
    )
    def test_is_latam_country(self, country: str, expected: bool):
        assert pd.is_latam_country(country) is expected

    def test_tier_d_hint_detects_youth_league(self):
        assert pd._tier_d_hint({"country": "Chile", "league_name": "U20 League", "liga": ""}) is True
        assert pd._tier_d_hint({"country": "Chile", "league_name": "Primera", "liga": ""}) is False


class TestCountOddsStats:
    def test_empty_response_with_errors(self):
        bm, mk, msg = pd._count_odds_stats({"errors": {"plan": "free"}})
        assert bm == 0
        assert mk == 0
        assert "errors" in (msg or "")

    def test_empty_response_without_errors(self):
        bm, mk, msg = pd._count_odds_stats({"response": []})
        assert bm == 0
        assert "empty response" in (msg or "")

    def test_counts_bookmakers_and_markets(self):
        payload = {
            "response": [
                {
                    "bookmakers": [
                        {"bets": [{"id": 1}, {"id": 2}]},
                        {"bets": [{"id": 3}]},
                    ]
                }
            ]
        }
        bm, mk, msg = pd._count_odds_stats(payload)
        assert bm == 2
        assert mk == 3
        assert msg is None

    def test_no_bookmakers_message(self):
        bm, mk, msg = pd._count_odds_stats({"response": [{"bookmakers": []}]})
        assert bm == 0
        assert "no bookmakers" in (msg or "")


class TestPrimaryDiscardReason:
    def test_branches(self):
        assert pd._primary_discard_reason(parsed=False, mock_picks_count=0, in_fixtures=False) == "not_in_fixtures_for_date"
        assert pd._primary_discard_reason(parsed=False, mock_picks_count=1, in_fixtures=True) == "invalid_fixture_row"
        assert pd._primary_discard_reason(parsed=True, mock_picks_count=0, in_fixtures=True) == "mock_no_ev_lines"
        assert pd._primary_discard_reason(parsed=True, mock_picks_count=2, in_fixtures=True) is None


class TestTraceFixture:
    def test_trace_chile_fixture_without_odds(self):
        settings = make_test_settings()
        item = make_api_football_fixture(country="Chile", league_name="Primera División")
        trace = pd.trace_fixture(item, settings, fetch_odds=False, query_date_utc=date(2030, 6, 1))
        assert trace["country"] == "Chile"
        assert trace["parsed"] is True
        assert trace["mock_picks_count"] >= 0

    def test_trace_with_odds_success(self):
        settings = make_test_settings()
        item = make_api_football_fixture(fixture_id=555, country="Argentina")
        odds_payload = {"response": [{"bookmakers": [{"bets": [{"id": 1}]}]}]}
        with patch("app.services.pipeline_debug.fetch_odds_by_fixture", return_value=odds_payload):
            trace = pd.trace_fixture(item, settings, fetch_odds=True, query_date_utc=date(2030, 6, 1))
        assert trace["has_odds"] is True
        assert trace["bookmakers_count"] == 1

    def test_trace_with_odds_api_error(self):
        settings = make_test_settings()
        item = make_api_football_fixture(fixture_id=556, country="Chile")
        with patch(
            "app.services.pipeline_debug.fetch_odds_by_fixture",
            side_effect=FootballApiError("429"),
        ):
            trace = pd.trace_fixture(item, settings, fetch_odds=True, query_date_utc=date(2030, 6, 1))
        assert trace["has_odds"] is False
        assert trace["odds_fetch_error"] == "429"

    def test_trace_invalid_fixture(self):
        settings = make_test_settings()
        trace = pd.trace_fixture({"fixture": {}}, settings, fetch_odds=False, query_date_utc=date(2030, 6, 1))
        assert trace["parsed"] is False
        assert trace["generates_ev_picks"] is False


class TestBuildLatamDebugReport:
    def test_build_report_filters_latam(self):
        settings = make_test_settings()
        chile = make_api_football_fixture(country="Chile", league_id=265)
        england = make_api_football_fixture(country="England", league_id=39)
        payload = {"response": [chile, england]}

        with patch(
            "app.services.football_api.fetch_fixtures_by_date_cached",
            return_value=payload,
        ):
            report = pd.build_latam_debug_report(settings, date(2030, 6, 1), fetch_odds=False)

        assert report["upstream"]["total_fixtures_all_countries"] == 2
        assert report["upstream"]["latam_fixtures_found"] == 1
        assert report["summary"]["fixtures_found"] == 1
        assert report["priority_leagues"]

    def test_build_report_non_list_response(self):
        settings = make_test_settings()
        with patch(
            "app.services.football_api.fetch_fixtures_by_date_cached",
            return_value={"response": "bad"},
        ):
            report = pd.build_latam_debug_report(settings, date(2030, 6, 1), fetch_odds=False)
        assert report["summary"]["fixtures_found"] == 0


class TestLogAllFixturesPipeline:
    def test_skips_non_latam_when_filtered(self):
        settings = make_test_settings()
        england = make_api_football_fixture(country="England")
        with patch("app.services.pipeline_debug.trace_fixture") as trace_mock:
            pd.log_all_fixtures_pipeline([england], settings, date(2030, 6, 1), latam_only=True)
        trace_mock.assert_not_called()

    def test_traces_latam_fixtures(self):
        settings = make_test_settings()
        chile = make_api_football_fixture(country="Chile")
        with patch("app.services.pipeline_debug.trace_fixture") as trace_mock:
            pd.log_all_fixtures_pipeline([chile, {"not": "dict"}], settings, date(2030, 6, 1))
        trace_mock.assert_called_once()
