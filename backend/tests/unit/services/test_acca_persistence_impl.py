"""Pruebas de acca_persistence_impl con sesiones SQLAlchemy simuladas."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services import acca_persistence_impl as impl
from tests.fixtures.settings import make_test_settings


def _sample_result(*, picks: list | None = None) -> dict:
    default_pick = {
        "fixture_id": 9001,
        "liga": "Primera División",
        "equipo_local": "Colo Colo",
        "equipo_visitante": "U. Chile",
        "fecha": "2030-06-01T20:00:00Z",
        "mercado": "1X2",
        "pick": "Local",
        "probabilidad": 0.55,
        "implied_probability": 0.48,
        "ev": 0.07,
        "confidence_pct": 72.0,
    }
    return {
        "date": "2030-06-01",
        "risk": "medium",
        "total_odds": 2.4,
        "combined_ev": 0.12,
        "combined_ev_pct": 12.0,
        "confidence_score": 0.7,
        "risk_score": 0.3,
        "volatility_score": 0.2,
        "model_version": "poisson-v1",
        "picks": picks if picks is not None else [default_pick],
    }


@contextmanager
def _mock_session_scope(session: MagicMock | None):
    @contextmanager
    def _scope(_url: str):
        yield session

    with patch.object(impl, "session_scope", _scope):
        yield


class TestParseKickoffUtc:
    def test_none_and_invalid(self):
        assert impl._parse_kickoff_utc(None) is None
        assert impl._parse_kickoff_utc("") is None
        assert impl._parse_kickoff_utc("not-a-date") is None

    def test_z_suffix_and_naive(self):
        dt = impl._parse_kickoff_utc("2030-06-01T18:00:00Z")
        assert dt is not None
        assert dt.tzinfo == timezone.utc

        naive = impl._parse_kickoff_utc("2030-06-01T18:00:00")
        assert naive is not None
        assert naive.tzinfo == timezone.utc


class TestPersistSmartAcca:
    def test_no_database_url(self):
        settings = make_test_settings().model_copy(update={"database_url": None})
        acca_id, detail = impl.persist_smart_acca(settings, _sample_result(), user_id=1)
        assert acca_id is None
        assert detail == "no_database_url"

    def test_no_picks(self):
        settings = make_test_settings()
        acca_id, detail = impl.persist_smart_acca(settings, _sample_result(picks=[]), user_id=1)
        assert acca_id is None
        assert detail == "no_picks_to_persist"

    def test_login_required(self):
        settings = make_test_settings()
        acca_id, detail = impl.persist_smart_acca(settings, _sample_result(), user_id=None)
        assert acca_id is None
        assert detail == "login_required"

    def test_session_unavailable(self):
        settings = make_test_settings()
        with _mock_session_scope(None):
            acca_id, detail = impl.persist_smart_acca(settings, _sample_result(), user_id=1)
        assert acca_id is None
        assert detail == "session_unavailable_engine_null"

    def test_success_persist_and_verify(self):
        settings = make_test_settings()
        session = MagicMock()
        history_row = MagicMock(created_at=datetime(2030, 6, 1, tzinfo=timezone.utc))
        session.get.side_effect = [MagicMock(), history_row]

        with _mock_session_scope(session):
            acca_id, warning = impl.persist_smart_acca(settings, _sample_result(), user_id=7)

        assert acca_id is not None
        assert warning is None
        session.add.assert_called()
        session.flush.assert_called()
        session.execute.assert_called()

    def test_invalid_date_still_persists(self):
        settings = make_test_settings()
        session = MagicMock()
        history_row = MagicMock(created_at=None)
        session.get.side_effect = [MagicMock(), history_row]
        payload = _sample_result()
        payload["date"] = "invalid-date"

        with _mock_session_scope(session):
            acca_id, warning = impl.persist_smart_acca(settings, payload, user_id=1)

        assert acca_id is not None
        assert warning is None

    def test_persist_exception_returns_error_detail(self):
        settings = make_test_settings()
        session = MagicMock()
        session.add.side_effect = RuntimeError("db down")

        with _mock_session_scope(session):
            acca_id, detail = impl.persist_smart_acca(settings, _sample_result(), user_id=1)

        assert acca_id is None
        assert detail is not None
        assert "RuntimeError" in detail

    def test_post_commit_verify_missing_row(self):
        settings = make_test_settings()
        write_session = MagicMock()
        write_session.get.return_value = MagicMock()
        verify_session = MagicMock()
        verify_session.get.return_value = None

        sessions = iter([write_session, verify_session])

        @contextmanager
        def _scope(_url: str):
            yield next(sessions)

        with patch.object(impl, "session_scope", _scope):
            acca_id, warning = impl.persist_smart_acca(settings, _sample_result(), user_id=1)

        assert acca_id is not None
        assert warning == "post_commit_select_acca_history_missing"

    def test_skips_prediction_without_fixture_id(self):
        settings = make_test_settings()
        session = MagicMock()
        session.get.side_effect = [MagicMock(), MagicMock(created_at=None)]
        payload = _sample_result(
            picks=[
                {"mercado": "1X2", "pick": "X"},
                _sample_result()["picks"][0],
            ]
        )

        with _mock_session_scope(session):
            acca_id, warning = impl.persist_smart_acca(settings, payload, user_id=1)

        assert acca_id is not None


class TestFetchAccaDbLastDebug:
    def test_stateless_without_database_url(self):
        settings = make_test_settings().model_copy(update={"database_url": None})
        payload = impl.fetch_acca_db_last_debug(settings)
        assert payload["mode"] == "stateless"

    def test_session_unavailable(self):
        settings = make_test_settings()
        with _mock_session_scope(None):
            payload = impl.fetch_acca_db_last_debug(settings)
        assert payload["mode"] == "error"
        assert payload["detail"] == "database_unavailable"

    def test_connected_with_rows(self):
        settings = make_test_settings()
        session = MagicMock()
        session.scalar.side_effect = [3, 10]
        acca = MagicMock(
            acca_id="a1",
            risk_profile="medium",
            fixture_date=date(2030, 6, 1),
            total_odds=2.5,
            status="pending",
            created_at=datetime(2030, 6, 1, tzinfo=timezone.utc),
        )
        pred = MagicMock(
            id=99,
            acca_id="a1",
            fixture_id=9001,
            market="1X2: Local",
            created_at=datetime(2030, 6, 1, tzinfo=timezone.utc),
        )
        acca_scalars = MagicMock()
        acca_scalars.first.return_value = acca
        pred_scalars = MagicMock()
        pred_scalars.first.return_value = pred
        session.scalars.side_effect = [acca_scalars, pred_scalars]

        with _mock_session_scope(session):
            payload = impl.fetch_acca_db_last_debug(settings)

        assert payload["mode"] == "connected"
        assert payload["total_acca_history"] == 3
        assert payload["last_acca"]["acca_id"] == "a1"
        assert payload["last_prediction"]["fixture_id"] == 9001

    def test_connected_without_rows(self):
        settings = make_test_settings()
        session = MagicMock()
        session.scalar.side_effect = [0, 0]
        empty = MagicMock()
        empty.first.return_value = None
        session.scalars.side_effect = [empty, empty]

        with _mock_session_scope(session):
            payload = impl.fetch_acca_db_last_debug(settings)

        assert payload["mode"] == "connected"
        assert payload["last_acca"] is None
        assert payload["last_prediction"] is None

    def test_exception_returns_generic_error(self):
        settings = make_test_settings()
        session = MagicMock()
        session.scalar.side_effect = RuntimeError("boom")

        with _mock_session_scope(session):
            payload = impl.fetch_acca_db_last_debug(settings)

        assert payload["mode"] == "error"
        assert payload["detail"] == "database_unavailable"


class TestListAccaHistory:
    def test_returns_empty_without_user_or_url(self):
        settings = make_test_settings().model_copy(update={"database_url": None})
        assert impl.list_acca_history(settings) == []
        assert impl.list_acca_history(make_test_settings(), user_id=None) == []

    def test_success_with_rows(self):
        settings = make_test_settings()
        row = MagicMock(
            acca_id="x1",
            fixture_date=date(2030, 6, 1),
            risk_profile="high",
            total_odds=4.0,
            combined_ev_pct=15.0,
            confidence_score=0.8,
            picks_json=[{"fixture_id": 1}],
            created_at=datetime(2030, 6, 1, tzinfo=timezone.utc),
            model_version="v1",
            status="pending",
        )
        session = MagicMock()
        session.scalars.return_value.all.return_value = [row]

        with _mock_session_scope(session):
            items = impl.list_acca_history(settings, limit=500, user_id=3)

        assert len(items) == 1
        assert items[0]["acca_id"] == "x1"
        assert items[0]["pick_count"] == 1

    def test_exception_returns_empty_list(self):
        settings = make_test_settings()
        session = MagicMock()
        session.scalars.side_effect = RuntimeError("read fail")

        with _mock_session_scope(session):
            assert impl.list_acca_history(settings, user_id=1) == []

    def test_limit_is_clamped(self):
        settings = make_test_settings()
        session = MagicMock()
        session.scalars.return_value.all.return_value = []

        with _mock_session_scope(session):
            impl.list_acca_history(settings, limit=0, user_id=1)

        session.scalars.assert_called_once()
