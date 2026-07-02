"""Pruebas de dependencias de autenticación FastAPI."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.deps.auth import get_current_user, get_optional_current_user
from app.db.models import UserRow
from app.services.auth_tokens import create_access_token
from tests.fixtures.settings import make_test_settings


class TestAuthDeps:
    def test_get_current_user_no_credentials(self):
        settings = make_test_settings()
        with pytest.raises(HTTPException) as exc:
            get_current_user(credentials=None, settings=settings)
        assert exc.value.status_code == 401

    def test_get_current_user_invalid_token(self):
        settings = make_test_settings()
        creds = MagicMock(scheme="Bearer", credentials="invalid")
        with pytest.raises(HTTPException) as exc:
            get_current_user(credentials=creds, settings=settings)
        assert exc.value.status_code == 401

    def test_get_current_user_success(self):
        settings = make_test_settings()
        user = UserRow(id=7, email="u@test.com", password_hash="h", display_name="U", tier="premium")
        token = create_access_token(user_id=7, settings=settings)
        creds = MagicMock(scheme="Bearer", credentials=token)

        @contextmanager
        def fake_scope(_url: str):
            session = MagicMock()
            with patch("app.api.deps.auth.get_user_by_id", return_value=user):
                yield session

        with patch("app.api.deps.auth.session_scope", fake_scope):
            public = get_current_user(credentials=creds, settings=settings)
        assert public.id == 7
        assert public.tier == "premium"

    def test_optional_user_returns_none_without_header(self):
        settings = make_test_settings()
        assert get_optional_current_user(credentials=None, settings=settings) is None

    def test_optional_user_returns_none_without_database(self):
        settings = make_test_settings(database_url=None)
        token = create_access_token(user_id=1, settings=settings)
        creds = MagicMock(scheme="Bearer", credentials=token)
        assert get_optional_current_user(credentials=creds, settings=settings) is None
