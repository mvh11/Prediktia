"""Pruebas de validación de esquemas de autenticación."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest, UserPublic


class TestRegisterRequest:
    def test_valid_register(self):
        req = RegisterRequest(email="user@example.com", password="password123")
        assert req.email == "user@example.com"

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password="short")

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="not-an-email", password="password123")


class TestLoginRequest:
    def test_valid_login(self):
        req = LoginRequest(email="user@example.com", password="x")
        assert req.password == "x"

    def test_empty_password_invalid(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com", password="")


class TestUserPublicTierNormalizer:
    def test_normalizes_unknown_tier_to_free(self):
        user = UserPublic(
            id=1,
            email="a@b.com",
            display_name="A",
            tier="legacy",  # type: ignore[arg-type]
        )
        assert user.tier == "free"

    def test_accepts_valid_tier(self):
        user = UserPublic(id=1, email="a@b.com", display_name="A", tier="premium")
        assert user.tier == "premium"
