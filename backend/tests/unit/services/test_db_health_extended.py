"""Pruebas ampliadas de db_health (build_db_health_payload y ramas de error)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.db_health import build_db_health_payload, database_status_message, inspect_db_health
from tests.fixtures.settings import make_test_settings


class TestBuildDbHealthPayload:
    def test_disabled_without_database_url(self):
        settings = make_test_settings().model_copy(update={"database_url": None})
        payload = build_db_health_payload(settings)
        assert payload["database"] == "disabled"
        assert payload["stateless"] is True

    def test_engine_none(self):
        settings = make_test_settings()
        with patch("app.services.db_health.get_engine", return_value=None):
            payload = build_db_health_payload(settings)
        assert payload["database"] == "error"
        assert "database_url_preview" in payload

    def test_connected_with_alembic_revision(self):
        settings = make_test_settings()
        conn = MagicMock()
        select_one = MagicMock()
        select_one.scalar.return_value = 1
        alembic = MagicMock()
        alembic.scalar.return_value = "20260101_001"
        conn.execute.side_effect = [select_one, alembic]
        cm = MagicMock()
        cm.__enter__.return_value = conn
        cm.__exit__.return_value = False
        engine = MagicMock()
        engine.connect.return_value = cm

        with patch("app.services.db_health.get_engine", return_value=engine), patch(
            "app.services.db_health._acca_history_ready", return_value=True
        ):
            payload = build_db_health_payload(settings)

        assert payload["database"] == "connected"
        assert payload["alembic_revision"] == "20260101_001"

    def test_migrations_pending_when_acca_history_missing(self):
        settings = make_test_settings()
        conn = MagicMock()
        conn.execute.return_value.scalar.return_value = 1
        cm = MagicMock()
        cm.__enter__.return_value = conn
        cm.__exit__.return_value = False
        engine = MagicMock()
        engine.connect.return_value = cm

        with patch("app.services.db_health.get_engine", return_value=engine), patch(
            "app.services.db_health._acca_history_ready", side_effect=[False, False]
        ), patch("app.services.db_health.ensure_database_schema", return_value=False), patch(
            "app.services.db_health.schema_bootstrap_error", return_value="migrate failed"
        ):
            payload = build_db_health_payload(settings)

        assert payload["database"] == "error"
        assert payload["migrations_pending"] is True

    def test_connection_exception_redacts_url(self):
        settings = make_test_settings()
        with patch("app.services.db_health.get_engine", side_effect=RuntimeError("connection refused")):
            payload = build_db_health_payload(settings)
        assert payload["database"] == "error"
        assert "database_url_preview" in payload
        assert "secret" not in payload["database_url_preview"]


class TestDatabaseStatusMessageExtended:
    def test_engine_unavailable(self):
        settings = make_test_settings()
        with patch("app.services.db_health.get_engine", return_value=None):
            assert database_status_message(settings) == "No hay historial disponible."

    def test_schema_not_ready_triggers_migrate(self):
        settings = make_test_settings()
        conn = MagicMock()
        conn.execute.return_value.scalar.return_value = 1
        cm = MagicMock()
        cm.__enter__.return_value = conn
        cm.__exit__.return_value = False
        engine = MagicMock()
        engine.connect.return_value = cm

        with patch("app.services.db_health.get_engine", return_value=engine), patch(
            "app.services.db_health._acca_history_ready", side_effect=[False, True]
        ), patch("app.services.db_health.ensure_database_schema", return_value=True):
            assert database_status_message(settings) is None


class TestInspectDbHealthExtended:
    def test_error_when_engine_none(self):
        settings = make_test_settings()
        with patch("app.services.db_health.get_engine", return_value=None):
            payload = inspect_db_health(settings)
        assert payload["database"] == "error"

    def test_exception_returns_error(self):
        settings = make_test_settings()
        with patch("app.services.db_health.get_engine", side_effect=RuntimeError("boom")):
            payload = inspect_db_health(settings)
        assert payload["database"] == "error"
