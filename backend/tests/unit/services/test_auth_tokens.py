"""Pruebas de tokens JWT."""

from __future__ import annotations

from datetime import timedelta

import jwt
import pytest

from app.config import Settings
from app.services.auth_tokens import create_access_token, decode_access_token


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        api_football_key="test-key",
        jwt_secret="unit-test-secret",
        jwt_expire_minutes=30,
    )


class TestAuthTokens:
    def test_create_and_decode_roundtrip(self, auth_settings):
        token = create_access_token(user_id=42, settings=auth_settings)
        user_id = decode_access_token(token, auth_settings)
        assert user_id == 42

    def test_decode_invalid_token_returns_none(self, auth_settings):
        assert decode_access_token("invalid.token.here", auth_settings) is None

    def test_decode_wrong_secret_returns_none(self, auth_settings):
        token = create_access_token(user_id=7, settings=auth_settings)
        other = Settings(api_football_key="k", jwt_secret="other-secret")
        assert decode_access_token(token, other) is None

    def test_expired_token_returns_none(self, auth_settings):
        expired_settings = Settings(
            api_football_key="test-key",
            jwt_secret=auth_settings.jwt_secret,
            jwt_expire_minutes=-1,
        )
        token = create_access_token(user_id=1, settings=expired_settings)
        assert decode_access_token(token, auth_settings) is None

    def test_token_contains_expected_claims(self, auth_settings):
        token = create_access_token(user_id=99, settings=auth_settings)
        payload = jwt.decode(token, auth_settings.jwt_secret, algorithms=["HS256"])
        assert payload["sub"] == "99"
        assert "exp" in payload
