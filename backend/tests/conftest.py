"""Fixtures compartidas para la suite pytest de Prediktia."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Garantiza que `import app` resuelva el paquete del backend.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def sample_api_fixture() -> dict:
    """Fila mínima compatible con API-Football /fixtures."""
    from tests.fixtures.api_football import make_api_football_fixture

    return make_api_football_fixture(
        fixture_id=900001,
        league_id=265,
        league_name="Primera División",
        country="Chile",
        home_name="Colo Colo",
        away_name="Universidad de Chile",
    )


@pytest.fixture
def test_settings():
    from tests.fixtures.settings import make_test_settings

    return make_test_settings()


@pytest.fixture
def premium_user():
    from app.schemas.auth import UserPublic

    return UserPublic(
        id=1,
        email="premium@test.com",
        display_name="Premium User",
        tier="premium",
        tier_label="Premium",
    )


@pytest.fixture
def free_user():
    from app.schemas.auth import UserPublic

    return UserPublic(
        id=2,
        email="free@test.com",
        display_name="Free User",
        tier="free",
        tier_label="Free",
    )


@pytest.fixture(autouse=True)
def reset_football_api_caches():
    """Evita interferencia entre tests que usan caché en memoria de football_api."""
    import app.services.football_api as fa

    with fa._cache_lock:
        fa._fixtures_cache.clear()
        fa._fixtures_cache_ts.clear()
        fa._odds_cache.clear()
        fa._odds_cache_ts.clear()
    with fa._sf_lock:
        fa._sf_fixtures.clear()
        fa._sf_fixtures_result.clear()
        fa._sf_odds.clear()
        fa._sf_odds_result.clear()
    yield
    with fa._cache_lock:
        fa._fixtures_cache.clear()
        fa._fixtures_cache_ts.clear()
        fa._odds_cache.clear()
        fa._odds_cache_ts.clear()
    with fa._sf_lock:
        fa._sf_fixtures.clear()
        fa._sf_fixtures_result.clear()
        fa._sf_odds.clear()
        fa._sf_odds_result.clear()


@pytest.fixture
def client(test_settings) -> Generator[TestClient, None, None]:
    from app.config import get_settings
    from app.main import create_app

    dev_settings = test_settings.model_copy(update={"app_env": "development"})
    app = create_app(dev_settings)
    app.dependency_overrides[get_settings] = lambda: dev_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@contextmanager
def mock_session_scope(session: MagicMock):
    """Context manager para parchear session_scope en rutas."""
    from unittest.mock import patch

    @contextmanager
    def _fake_scope(_url: str):
        yield session

    with patch("app.api.routes.auth.session_scope", _fake_scope), patch(
        "app.api.routes.payments.session_scope",
        _fake_scope,
    ):
        yield
