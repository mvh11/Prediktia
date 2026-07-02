"""Pruebas de health DB y mensajes de estado."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.db_health import (
    _redact_database_url,
    database_connected,
    database_status_message,
    inspect_db_health,
)
from tests.fixtures.settings import make_test_settings


class TestDbHealth:
    def test_redact_database_url(self):
        url = "postgresql://user:secret@host/db"
        redacted = _redact_database_url(url)
        assert "secret" not in redacted
        assert "user" in redacted

    def test_database_connected_no_url(self):
        settings = make_test_settings().model_copy(update={"database_url": None})
        assert database_connected(settings) is False

    def test_database_connected_with_engine(self):
        settings = make_test_settings()
        conn = MagicMock()
        conn.execute.return_value.scalar.side_effect = ["acca_history", 1]
        cm = MagicMock()
        cm.__enter__.return_value = conn
        cm.__exit__.return_value = False
        engine = MagicMock()
        engine.connect.return_value = cm
        with patch("app.services.db_health.get_engine", return_value=engine):
            assert database_connected(settings) is True

    def test_database_status_message_no_url(self):
        settings = make_test_settings().model_copy(update={"database_url": None})
        assert database_status_message(settings) == "No hay historial disponible."

    def test_inspect_db_health_disabled(self):
        settings = make_test_settings().model_copy(update={"database_url": None})
        payload = inspect_db_health(settings)
        assert payload["database"] == "disabled"

    def test_inspect_db_health_ok(self):
        settings = make_test_settings()
        conn = MagicMock()
        conn.execute.return_value.scalar.side_effect = ["acca_history", 1]
        cm = MagicMock()
        cm.__enter__.return_value = conn
        cm.__exit__.return_value = False
        engine = MagicMock()
        engine.connect.return_value = cm
        with patch("app.services.db_health.get_engine", return_value=engine):
            payload = inspect_db_health(settings)
        assert payload["database"] == "ok"
        assert payload["acca_history_exists"] is True
