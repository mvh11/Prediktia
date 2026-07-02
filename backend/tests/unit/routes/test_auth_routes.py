"""Pruebas de rutas de autenticación."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps.auth import get_current_user
from app.config import get_settings
from app.db.models import UserRow
from tests.fixtures.settings import make_test_settings


@contextmanager
def _session_override(session: MagicMock):
    @contextmanager
    def fake_scope(_url: str):
        yield session

    with patch("app.api.routes.auth.session_scope", fake_scope):
        yield


class TestAuthRoutes:
    def test_register_requires_database(self, client: TestClient):
        no_db = make_test_settings().model_copy(update={"database_url": None, "app_env": "development"})
        client.app.dependency_overrides[get_settings] = lambda: no_db
        res = client.post(
            "/auth/register",
            json={"email": "a@b.com", "password": "password123"},
        )
        assert res.status_code == 503

    def test_register_success(self, client: TestClient):
        session = MagicMock()
        user = UserRow(
            id=10,
            email="new@test.com",
            password_hash="hash",
            display_name="New",
            tier="free",
        )
        with _session_override(session), patch(
            "app.api.routes.auth.get_user_by_email",
            return_value=None,
        ), patch("app.api.routes.auth.create_user", return_value=user):
            res = client.post(
                "/auth/register",
                json={"email": "new@test.com", "password": "password123"},
            )
        assert res.status_code == 201
        body = res.json()
        assert body["access_token"]
        assert body["user"]["email"] == "new@test.com"

    def test_register_conflict(self, client: TestClient):
        session = MagicMock()
        existing = UserRow(id=1, email="x@y.com", password_hash="h", display_name="X")
        with _session_override(session), patch(
            "app.api.routes.auth.get_user_by_email",
            return_value=existing,
        ):
            res = client.post(
                "/auth/register",
                json={"email": "x@y.com", "password": "password123"},
            )
        assert res.status_code == 409

    def test_login_invalid_credentials(self, client: TestClient):
        session = MagicMock()
        with _session_override(session), patch(
            "app.api.routes.auth.authenticate_user",
            return_value=None,
        ):
            res = client.post(
                "/auth/login",
                json={"email": "x@y.com", "password": "wrong"},
            )
        assert res.status_code == 401

    def test_login_success(self, client: TestClient):
        session = MagicMock()
        user = UserRow(id=5, email="ok@test.com", password_hash="h", display_name="OK", tier="free")
        with _session_override(session), patch(
            "app.api.routes.auth.authenticate_user",
            return_value=user,
        ):
            res = client.post(
                "/auth/login",
                json={"email": "ok@test.com", "password": "secret123"},
            )
        assert res.status_code == 200
        assert res.json()["user"]["id"] == 5

    def test_me_requires_auth(self, client: TestClient):
        res = client.get("/auth/me")
        assert res.status_code == 401

    def test_me_with_override(self, client: TestClient, premium_user):
        client.app.dependency_overrides[get_current_user] = lambda: premium_user
        try:
            res = client.get("/auth/me")
        finally:
            client.app.dependency_overrides.pop(get_current_user, None)
        assert res.status_code == 200
        assert res.json()["tier"] == "premium"

    def test_update_me(self, client: TestClient, premium_user):
        session = MagicMock()
        updated = UserRow(
            id=premium_user.id,
            email=premium_user.email,
            password_hash="h",
            display_name="Nuevo Nombre",
            tier="premium",
        )
        client.app.dependency_overrides[get_current_user] = lambda: premium_user
        try:
            with _session_override(session), patch(
                "app.api.routes.auth.update_user_display_name",
                return_value=updated,
            ):
                res = client.patch("/auth/me", json={"display_name": "Nuevo Nombre"})
        finally:
            client.app.dependency_overrides.pop(get_current_user, None)
        assert res.status_code == 200
        assert res.json()["display_name"] == "Nuevo Nombre"

    def test_change_password_wrong_current(self, client: TestClient, premium_user):
        session = MagicMock()
        client.app.dependency_overrides[get_current_user] = lambda: premium_user
        try:
            with _session_override(session), patch(
                "app.api.routes.auth.change_user_password",
                return_value=None,
            ):
                res = client.patch(
                    "/auth/me/password",
                    json={"current_password": "bad", "new_password": "newpassword123"},
                )
        finally:
            client.app.dependency_overrides.pop(get_current_user, None)
        assert res.status_code == 400
