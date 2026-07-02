"""Pruebas de rutas FastAPI con TestClient."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from tests.fixtures.api_football import make_api_football_fixture


def _fixtures_payload(count: int = 3) -> dict:
    future_ts = int(datetime(2030, 6, 1, 18, 0, tzinfo=timezone.utc).timestamp())
    return {
        "response": [
            make_api_football_fixture(fixture_id=1000 + i, timestamp=future_ts + i * 3600)
            for i in range(count)
        ],
        "_prediktia_cache": {"cache_hit": True, "stale": False, "rate_limited": False},
    }


class TestMainRoutes:
    def test_health(self, client: TestClient):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_health_db_disabled(self, client: TestClient, test_settings):
        test_settings.database_url = None
        res = client.get("/health/db")
        assert res.status_code == 200
        body = res.json()
        assert body.get("database") in ("disabled", "ok", "error")

    def test_openapi_json(self, client: TestClient):
        res = client.get("/openapi.json")
        assert res.status_code == 200
        assert "openapi" in res.json()


class TestMatchesRoutes:
    def test_list_matches_default(self, client: TestClient):
        with patch(
            "app.api.routes.matches.fetch_fixtures_by_date_cached",
            return_value=_fixtures_payload(2),
        ):
            res = client.get("/matches")
        assert res.status_code == 200
        body = res.json()
        assert body["results_count"] == 2
        assert len(body["raw_fixtures"]) == 2

    def test_list_matches_invalid_date(self, client: TestClient):
        res = client.get("/matches", params={"date": "not-a-date"})
        assert res.status_code == 400


class TestValueBetsRoutes:
    def test_list_value_bets(self, client: TestClient, premium_user):
        from app.api.deps.auth import get_optional_current_user

        client.app.dependency_overrides[get_optional_current_user] = lambda: premium_user
        try:
            with patch(
                "app.api.routes.value_bets.fetch_fixtures_by_date_cached",
                return_value=_fixtures_payload(4),
            ), patch(
                "app.api.routes.value_bets.filter_and_sort_fixtures_for_acca",
                side_effect=lambda fixtures, **_: (fixtures, {}, {}),
            ):
                res = client.get("/value-bets")
        finally:
            client.app.dependency_overrides.pop(get_optional_current_user, None)

        assert res.status_code == 200
        body = res.json()
        assert body["plan_tier"] == "premium"
        assert body["plan_limited"] is False
        assert body["picks_count"] >= 0

    def test_value_bets_free_tier_limited(self, client: TestClient):
        with patch(
            "app.api.routes.value_bets.fetch_fixtures_by_date_cached",
            return_value=_fixtures_payload(6),
        ), patch(
            "app.api.routes.value_bets.filter_and_sort_fixtures_for_acca",
            side_effect=lambda fixtures, **_: (fixtures, {}, {}),
        ):
            res = client.get("/value-bets")
        assert res.status_code == 200
        body = res.json()
        assert body["plan_tier"] == "free"
        assert body["plan_limited"] is True
        assert body["picks_count"] <= 3


class TestAccaRoutes:
    def test_acca_blocked_for_free(self, client: TestClient, free_user):
        from app.api.deps.auth import get_optional_current_user

        client.app.dependency_overrides[get_optional_current_user] = lambda: free_user
        try:
            res = client.get("/acca", params={"risk": "medium"})
        finally:
            client.app.dependency_overrides.pop(get_optional_current_user, None)
        assert res.status_code == 200
        body = res.json()
        assert body["pick_count"] == 0
        assert "Premium" in (body.get("message") or "")

    def test_acca_premium_generates(self, client: TestClient, premium_user):
        from app.api.deps.auth import get_optional_current_user

        client.app.dependency_overrides[get_optional_current_user] = lambda: premium_user
        try:
            with patch(
                "app.api.routes.acca.generate_acca_for_date",
                return_value={
                    "date": "2030-06-01",
                    "model_version": "poisson-v1+ev-simple",
                    "risk": "medium",
                    "risk_label": "Medio",
                    "profile": {"min_picks": 3, "max_picks": 3, "target_odds_range": "3 – 10"},
                    "picks": [],
                    "pick_count": 0,
                    "total_odds": 1.0,
                    "combined_probability": 0.0,
                    "combined_ev": 0.0,
                    "combined_ev_pct": 0.0,
                    "confidence_score": 0.0,
                    "risk_score": 0.0,
                    "volatility_score": 0.0,
                    "message": "test",
                    "meta": {
                        "candidates_pool_size": 0,
                        "eligible_after_filters": 0,
                        "bookmaker_odds_picks": 0,
                        "independence_assumption": "x",
                        "fetch_odds": False,
                        "fixtures_upstream_total": 0,
                        "fixtures_after_schedule_filter": 0,
                        "fixtures_after_schedule_strict": 0,
                        "schedule_filter_fallback": False,
                        "schedule_discard_reasons": {},
                        "fixtures_source": "api_football",
                        "requested_date": "2030-06-01",
                        "resolved_date": "2030-06-01",
                        "auto_shifted_date": False,
                        "unique_fixtures_count": 0,
                        "risk_profile_validation": {},
                        "persist_status": "skipped",
                        "persist_error": None,
                    },
                },
            ), patch("app.api.routes.acca.persist_smart_acca", return_value=(None, "no_database_url")):
                res = client.get("/acca", params={"risk": "medium", "date": "2030-06-01"})
        finally:
            client.app.dependency_overrides.pop(get_optional_current_user, None)
        assert res.status_code == 200
        assert res.json()["risk"] == "medium"

    def test_acca_history_requires_auth(self, client: TestClient, test_settings):
        with patch("app.api.routes.acca.database_connected", return_value=True):
            res = client.get("/acca/history")
        assert res.status_code == 200
        body = res.json()
        assert body["requires_auth"] is True

    def test_acca_invalid_date(self, client: TestClient, premium_user):
        from app.api.deps.auth import get_optional_current_user

        client.app.dependency_overrides[get_optional_current_user] = lambda: premium_user
        try:
            res = client.get("/acca", params={"date": "bad-date"})
        finally:
            client.app.dependency_overrides.pop(get_optional_current_user, None)
        assert res.status_code == 400
