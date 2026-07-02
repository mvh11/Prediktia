"""Pruebas de capa de persistencia ACCA (sin PostgreSQL real)."""

from __future__ import annotations

from unittest.mock import patch

from app.services import acca_persistence as ap
from tests.fixtures.settings import make_test_settings


class TestAccaPersistenceFacade:
    def setup_method(self):
        ap._db_impl = None

    def test_persist_without_database_url(self):
        settings = make_test_settings().model_copy(update={"database_url": None})
        acca_id, detail = ap.persist_smart_acca(settings, {"pick_count": 1, "picks": [{}]})
        assert acca_id is None
        assert detail == "no_database_url"

    def test_list_history_without_database_url(self):
        settings = make_test_settings().model_copy(update={"database_url": None})
        assert ap.list_acca_history(settings) == []

    def test_persist_delegates_to_impl(self):
        settings = make_test_settings()
        with patch.object(ap, "_resolve_db_impl", return_value=(lambda *a, **k: ("id-1", None), lambda *a, **k: [])):
            acca_id, detail = ap.persist_smart_acca(settings, {"pick_count": 0, "picks": []})
        assert acca_id == "id-1"
        assert detail is None

    def test_list_delegates_to_impl(self):
        settings = make_test_settings()
        rows = [{"acca_id": "x"}]
        with patch.object(ap, "_resolve_db_impl", return_value=(lambda *a, **k: (None, None), lambda *a, **k: rows)):
            assert ap.list_acca_history(settings, limit=5) == rows
