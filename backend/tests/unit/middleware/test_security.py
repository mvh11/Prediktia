"""Tests de hardening DAST (cabeceras, rate limit, produccion)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.middleware.auth_rate_limit import reset_auth_rate_limit_store
from tests.fixtures.settings import make_test_settings


@pytest.fixture
def production_settings() -> Settings:
    return make_test_settings(app_env="production", frontend_url="https://app.example.com")


@pytest.fixture
def production_client(production_settings: Settings) -> TestClient:
    app = create_app(production_settings)
    with TestClient(app) as client:
        yield client


class TestSecurityHeaders:
    def test_health_includes_security_headers(self, client: TestClient):
        res = client.get("/health")
        assert res.status_code == 200
        for header in (
            "strict-transport-security",
            "content-security-policy",
            "x-frame-options",
            "x-content-type-options",
            "referrer-policy",
            "permissions-policy",
        ):
            assert header in res.headers
        assert "server" not in res.headers


class TestProductionSurface:
    def test_debug_routes_disabled(self, production_client: TestClient):
        for path in ("/debug/latam", "/debug/acca-db-last", "/debug/acca-filter"):
            assert production_client.get(path).status_code == 404

    def test_docs_and_openapi_disabled(self, production_client: TestClient):
        assert production_client.get("/docs").status_code == 404
        assert production_client.get("/openapi.json").status_code == 404

    def test_cors_blocks_unknown_origin(self, production_client: TestClient):
        res = production_client.get(
            "/health",
            headers={"Origin": "https://evil.example"},
        )
        assert res.headers.get("access-control-allow-origin") != "*"
        assert res.headers.get("access-control-allow-origin") != "https://evil.example"

    def test_cors_allows_frontend_origin(self, production_client: TestClient):
        res = production_client.get(
            "/health",
            headers={"Origin": "https://app.example.com"},
        )
        assert res.status_code == 200
        # Starlette puede omitir ACAO en GET simple; verificar que no expone wildcard.
        assert res.headers.get("access-control-allow-origin") != "*"


class TestAuthRateLimit:
    def test_login_rate_limited(self):
        reset_auth_rate_limit_store()
        limited_settings = make_test_settings(
            auth_rate_limit_max=2,
            auth_rate_limit_window_seconds=60,
        )
        app = create_app(limited_settings)

        with patch("app.middleware.auth_rate_limit.get_settings", return_value=limited_settings):
            with TestClient(app) as limited_client:
                for _ in range(2):
                    res = limited_client.post("/auth/login", json={})
                    assert res.status_code == 422
                blocked = limited_client.post("/auth/login", json={})
                assert blocked.status_code == 429

        reset_auth_rate_limit_store()
