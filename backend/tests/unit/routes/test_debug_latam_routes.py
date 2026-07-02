"""Pruebas de rutas /debug/* con dependencias mockeadas."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.football_api import FootballApiError
from tests.fixtures.api_football import make_api_football_fixture
from tests.fixtures.settings import make_test_settings


@pytest.fixture
def debug_client(test_settings) -> TestClient:
    dev = test_settings.model_copy(update={"app_env": "development"})
    app = create_app(dev)
    app.dependency_overrides[get_settings] = lambda: dev
    return TestClient(app)


class TestDebugLatamRoutes:
    def test_acca_db_last(self, debug_client: TestClient):
        with patch(
            "app.api.routes.debug_latam.fetch_acca_db_last_debug",
            return_value={"mode": "connected", "total_acca_history": 1},
        ):
            res = debug_client.get("/debug/acca-db-last")
        assert res.status_code == 200
        assert res.json()["mode"] == "connected"

    def test_latam_success(self, debug_client: TestClient):
        report = {
            "timezone": {"backend_utc_now": "2030-06-01T00:00:00+00:00", "query_date_utc": "2030-06-01",
                        "date_param_semantics": "x", "fixture_timezone_samples": []},
            "upstream": {"total_fixtures_all_countries": 1, "latam_fixtures_found": 1, "latam_countries_in_scope": []},
            "summary": {"fixtures_found": 1, "fixtures_with_odds": 0, "fixtures_generating_mock_ev_picks": 1,
                        "fixtures_discarded": 0, "discard_by_reason": {}},
            "priority_leagues": [],
            "fixtures": [],
            "pipeline_notes": {},
        }
        with patch("app.api.routes.debug_latam.build_latam_debug_report", return_value=report):
            res = debug_client.get("/debug/latam?date=2030-06-01&fetch_odds=false")
        assert res.status_code == 200
        assert res.json()["summary"]["fixtures_found"] == 1

    def test_latam_upstream_error(self, debug_client: TestClient):
        with patch(
            "app.api.routes.debug_latam.build_latam_debug_report",
            side_effect=FootballApiError("upstream fail"),
        ):
            res = debug_client.get("/debug/latam")
        assert res.status_code == 502

    def test_latam_invalid_date(self, debug_client: TestClient):
        res = debug_client.get("/debug/latam?date=bad-date")
        assert res.status_code == 400

    def test_acca_filter_success(self, debug_client: TestClient):
        fixtures = [make_api_football_fixture()]
        with patch(
            "app.api.routes.debug_latam.fetch_fixtures_by_date_cached",
            return_value={"response": fixtures},
        ), patch(
            "app.api.routes.debug_latam.build_acca_filter_debug_report",
            return_value={"fixtures_total": 1},
        ):
            res = debug_client.get("/debug/acca-filter?date=2030-06-01")
        assert res.status_code == 200
        assert res.json()["fixtures_total"] == 1

    def test_acca_filter_upstream_error(self, debug_client: TestClient):
        with patch(
            "app.api.routes.debug_latam.fetch_fixtures_by_date_cached",
            side_effect=FootballApiError("429"),
        ):
            res = debug_client.get("/debug/acca-filter")
        assert res.status_code == 502

    def test_acca_filter_raw_non_list_response(self, debug_client: TestClient):
        with patch(
            "app.api.routes.debug_latam.fetch_fixtures_by_date_cached",
            return_value={"response": "invalid"},
        ), patch(
            "app.api.routes.debug_latam.build_acca_filter_raw_rows",
            return_value={"rows": []},
        ) as raw_mock:
            res = debug_client.get("/debug/acca-filter/raw")
        assert res.status_code == 200
        raw_mock.assert_called_once_with([], min_minutes_before_kickoff=0)
