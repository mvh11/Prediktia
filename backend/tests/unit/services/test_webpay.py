"""Pruebas del cliente Webpay (sin llamadas HTTP reales)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.config import Settings
from app.services.webpay import (
    WebpayError,
    commit_webpay_transaction,
    create_webpay_transaction,
    webpay_api_base,
)


@pytest.fixture
def webpay_settings() -> Settings:
    return Settings(
        api_football_key="test",
        webpay_env="integration",
        webpay_commerce_code="597055555532",
        webpay_api_key="579B532A7440BB0C9079DEDCF7D547610A17BE87481CA7D62EC99EC55EB1D1C0",
        webpay_return_url="https://api.example.com/payments/webpay/return",
        frontend_url="https://app.example.com",
    )


class TestWebpayApiBase:
    def test_integration_env(self, webpay_settings):
        assert "webpay3gint" in webpay_api_base(webpay_settings)

    def test_production_env(self, webpay_settings):
        webpay_settings.webpay_env = "production"
        assert "webpay3g.transbank.cl" in webpay_api_base(webpay_settings)
        assert "gint" not in webpay_api_base(webpay_settings)


class TestCreateWebpayTransaction:
    @patch("app.services.webpay.requests.post")
    def test_success(self, mock_post, webpay_settings):
        mock_post.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=lambda: {
                "token": "abc123",
                "url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction",
            },
        )
        result = create_webpay_transaction(
            webpay_settings,
            buy_order="P1001",
            session_id="s1",
            amount=4990,
            return_url=webpay_settings.webpay_return_url,
        )
        assert result["token"] == "abc123"
        assert "initTransaction" in result["url"]

    @patch("app.services.webpay.requests.post")
    def test_http_error_raises_webpay_error(self, mock_post, webpay_settings):
        mock_post.return_value = MagicMock(ok=False, status_code=422, text="error")
        with pytest.raises(WebpayError):
            create_webpay_transaction(
                webpay_settings,
                buy_order="P1001",
                session_id="s1",
                amount=4990,
                return_url=webpay_settings.webpay_return_url,
            )

    @patch("app.services.webpay.requests.post", side_effect=requests.Timeout("timeout"))
    def test_network_error_raises_webpay_error(self, _mock_post, webpay_settings):
        with pytest.raises(WebpayError, match="conectar"):
            create_webpay_transaction(
                webpay_settings,
                buy_order="P1001",
                session_id="s1",
                amount=4990,
                return_url=webpay_settings.webpay_return_url,
            )


class TestCommitWebpayTransaction:
    @patch("app.services.webpay.requests.put")
    def test_success(self, mock_put, webpay_settings):
        mock_put.return_value = MagicMock(
            ok=True,
            json=lambda: {"response_code": 0, "buy_order": "P1001"},
        )
        result = commit_webpay_transaction(webpay_settings, "token-xyz")
        assert result["response_code"] == 0
