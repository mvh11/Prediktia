"""Pruebas del cliente API-Football."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.services.football_api import (
    CACHE_META_KEY,
    CacheMeta,
    FootballApiError,
    extract_cache_meta,
    fetch_fixtures_by_date,
    fetch_fixtures_by_date_cached,
    fetch_fixtures_by_ids,
    fetch_odds_by_fixture_cached,
    peek_fixtures_cache,
)
from tests.fixtures.settings import make_test_settings


class TestExtractCacheMeta:
    def test_missing_meta_returns_defaults(self):
        meta = extract_cache_meta({"response": []})
        assert meta == CacheMeta()

    def test_reads_meta_fields(self):
        payload = {
            CACHE_META_KEY: {
                "cache_hit": True,
                "stale": True,
                "rate_limited": True,
                "warning": "stale data",
            }
        }
        meta = extract_cache_meta(payload)
        assert meta.cache_hit is True
        assert meta.stale is True
        assert meta.rate_limited is True
        assert meta.warning == "stale data"


class TestFetchFixturesByDate:
    def test_success(self):
        settings = make_test_settings()
        mock_resp = MagicMock(
            ok=True,
            status_code=200,
            text='{"response": [{"fixture": {"id": 1}}], "results": 1}',
            json=lambda: {"response": [{"fixture": {"id": 1}}], "results": 1},
        )
        with patch("app.services.football_api.requests.get", return_value=mock_resp):
            data = fetch_fixtures_by_date(settings, date(2026, 6, 1))
        assert len(data["response"]) == 1

    def test_missing_api_key_raises(self):
        settings = make_test_settings().model_copy(update={"api_football_key": ""})
        with pytest.raises(FootballApiError, match="API_FOOTBALL_KEY"):
            fetch_fixtures_by_date(settings, date(2026, 6, 1))

    def test_http_error_raises(self):
        settings = make_test_settings()
        mock_resp = MagicMock(ok=False, status_code=403, text="Forbidden")
        with patch("app.services.football_api.requests.get", return_value=mock_resp):
            with pytest.raises(FootballApiError):
                fetch_fixtures_by_date(settings, date(2026, 6, 1))

    def test_network_error_raises(self):
        settings = make_test_settings()
        with patch(
            "app.services.football_api.requests.get",
            side_effect=requests.Timeout("timeout"),
        ):
            with pytest.raises(FootballApiError, match="conectar"):
                fetch_fixtures_by_date(settings, date(2026, 6, 1))


class TestFetchFixturesCached:
    def test_cached_fetch_populates_cache(self):
        settings = make_test_settings()
        mock_resp = MagicMock(
            ok=True,
            status_code=200,
            text='{"response": [], "results": 0}',
            json=lambda: {"response": [], "results": 0},
        )
        with patch("app.services.football_api.requests.get", return_value=mock_resp):
            first = fetch_fixtures_by_date_cached(settings, date(2026, 7, 1))
            second = fetch_fixtures_by_date_cached(settings, date(2026, 7, 1))
        assert extract_cache_meta(first).cache_hit is False
        assert extract_cache_meta(second).cache_hit is True

    def test_stale_fallback_on_upstream_error(self):
        settings = make_test_settings()
        import app.services.football_api as fa

        fa._store_fixtures(
            "2026-08-01",
            {"response": [{"fixture": {"id": 99}}], "results": 1},
        )
        with patch(
            "app.services.football_api.fetch_fixtures_by_date",
            side_effect=FootballApiError("429", status_code=429),
        ), patch("app.services.football_api._get_fresh_fixtures", return_value=None):
            stale = fetch_fixtures_by_date_cached(settings, date(2026, 8, 1))
        meta = extract_cache_meta(stale)
        assert meta.stale is True
        assert meta.rate_limited is True
        assert len(stale["response"]) == 1

    def test_empty_fallback_without_prior_cache(self):
        settings = make_test_settings()
        err_resp = MagicMock(ok=False, status_code=500, text="error")
        with patch("app.services.football_api.requests.get", return_value=err_resp):
            payload = fetch_fixtures_by_date_cached(settings, date(2026, 9, 1))
        assert payload["response"] == []
        assert extract_cache_meta(payload).warning is not None


class TestPeekFixturesCache:
    def test_peek_after_store(self):
        settings = make_test_settings()
        mock_resp = MagicMock(
            ok=True,
            status_code=200,
            json=lambda: {"response": [{"fixture": {"id": 7}}], "results": 1},
        )
        with patch("app.services.football_api.requests.get", return_value=mock_resp):
            fetch_fixtures_by_date_cached(settings, date(2026, 10, 5))
        peeked = peek_fixtures_cache(date(2026, 10, 5))
        assert peeked is not None
        assert len(peeked["response"]) == 1


class TestFetchFixturesByIds:
    def test_empty_ids(self):
        settings = make_test_settings()
        assert fetch_fixtures_by_ids(settings, []) == {"response": []}

    def test_chunks_requests(self):
        settings = make_test_settings()
        mock_resp = MagicMock(
            ok=True,
            status_code=200,
            json=lambda: {"response": [{"fixture": {"id": 1}}]},
        )
        ids = list(range(1, 25))
        with patch("app.services.football_api.requests.get", return_value=mock_resp) as get:
            result = fetch_fixtures_by_ids(settings, ids)
        assert get.call_count == 2
        assert len(result["response"]) == 2


class TestFetchOddsCached:
    def test_odds_cached_fetch(self):
        settings = make_test_settings()
        mock_resp = MagicMock(
            ok=True,
            status_code=200,
            json=lambda: {"response": [{"bookmakers": []}]},
        )
        with patch("app.services.football_api.requests.get", return_value=mock_resp):
            first = fetch_odds_by_fixture_cached(settings, 12345)
            second = fetch_odds_by_fixture_cached(settings, 12345)
        assert first == second

    def test_odds_failure_returns_empty(self):
        settings = make_test_settings()
        err_resp = MagicMock(ok=False, status_code=429, text="limit")
        with patch("app.services.football_api.requests.get", return_value=err_resp):
            payload = fetch_odds_by_fixture_cached(settings, 999)
        assert payload.get("response") == []
