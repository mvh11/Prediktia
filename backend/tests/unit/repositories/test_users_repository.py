"""Pruebas del repositorio de usuarios (SQLAlchemy mockeado)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.db.models import UserRow
from app.services.users import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_tier,
)


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = MagicMock()
    return session


class TestUsersRepository:
    def test_get_user_by_email_normalizes(self, mock_session):
        user = UserRow(email="a@b.com", password_hash="hash", display_name="A")
        mock_session.scalar.return_value = user
        result = get_user_by_email(mock_session, "  A@B.COM  ")
        assert result is user

    def test_get_user_by_id(self, mock_session):
        user = UserRow(email="x@y.com", password_hash="hash", display_name="X")
        mock_session.get.return_value = user
        assert get_user_by_id(mock_session, 5) is user

    @patch("app.services.users.hash_password", return_value="hashed")
    def test_create_user_defaults(self, _mock_hash, mock_session):
        user = create_user(mock_session, email="New@Mail.com", password="secret123")
        mock_session.add.assert_called_once()
        assert user.email == "new@mail.com"
        assert user.tier == "free"
        assert user.display_name == "new"

    @patch("app.services.users.verify_password", return_value=True)
    def test_authenticate_user_success(self, _mock_verify, mock_session):
        user = UserRow(email="u@x.com", password_hash="hash", display_name="U")
        mock_session.scalar.return_value = user
        assert authenticate_user(mock_session, email="u@x.com", password="ok") is user

    @patch("app.services.users.verify_password", return_value=False)
    def test_authenticate_user_wrong_password(self, _mock_verify, mock_session):
        user = UserRow(email="u@x.com", password_hash="hash", display_name="U")
        mock_session.scalar.return_value = user
        assert authenticate_user(mock_session, email="u@x.com", password="bad") is None

    def test_update_user_tier(self, mock_session):
        user = UserRow(email="u@x.com", password_hash="hash", display_name="U", tier="free")
        mock_session.get.return_value = user
        updated = update_user_tier(mock_session, 1, "premium")
        assert updated is user
        assert user.tier == "premium"

    def test_update_user_tier_missing_user(self, mock_session):
        mock_session.get.return_value = None
        assert update_user_tier(mock_session, 999, "premium") is None
