"""Pruebas de filtros y normalizadores de fixtures ACCA."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.acca_fixture_filter import (
    fixture_status_reason,
    kickoff_in_minutes_from_now,
    kickoff_parse_source,
    parse_fixture_kickoff_utc,
)
from app.services.acca_fixture_filter import _normalize_fixture_timestamp
from tests.fixtures.api_football import make_api_football_fixture


class TestNormalizeFixtureTimestamp:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (1717200000, 1717200000),
            (1717200000000, 1717200000),
            ("1717200000", 1717200000),
            (0, None),
            (-5, None),
            (None, None),
            ("", None),
            ("abc", None),
            ([], None),
        ],
    )
    def test_normalize_timestamp(self, raw, expected):
        assert _normalize_fixture_timestamp(raw) == expected


class TestKickoffParseSource:
    def test_prefers_timestamp(self):
        item = make_api_football_fixture(timestamp=1893456000)
        assert kickoff_parse_source(item) == "timestamp"

    def test_falls_back_to_date(self):
        item = make_api_football_fixture()
        item["fixture"].pop("timestamp", None)
        assert kickoff_parse_source(item) == "date"

    def test_none_when_missing(self):
        item = {"fixture": {}}
        assert kickoff_parse_source(item) == "none"


class TestParseFixtureKickoffUtc:
    def test_parses_timestamp(self):
        ts = int(datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc).timestamp())
        item = make_api_football_fixture(timestamp=ts)
        kickoff = parse_fixture_kickoff_utc(item)
        assert kickoff is not None
        assert kickoff.tzinfo == timezone.utc

    def test_invalid_item_returns_none(self):
        assert parse_fixture_kickoff_utc({}) is None


class TestFixtureStatusReason:
    def test_prematch_allowed(self):
        item = make_api_football_fixture(status_short="NS")
        assert fixture_status_reason(item) is None

    def test_finished_rejected(self):
        item = make_api_football_fixture(status_short="FT")
        reason = fixture_status_reason(item)
        assert reason is not None
        assert "FT" in reason or reason != ""


class TestKickoffInMinutesFromNow:
    def test_future_fixture_positive_minutes(self):
        future_ts = int(datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc).timestamp())
        item = make_api_football_fixture(timestamp=future_ts)
        now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        mins = kickoff_in_minutes_from_now(item, now)
        assert mins is not None
        assert mins > 0
