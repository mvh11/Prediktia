"""Settings de prueba reutilizables."""

from __future__ import annotations

from app.config import Settings


def make_test_settings(**overrides) -> Settings:
    base = {
        "api_football_key": "test-api-key",
        "api_football_base_url": "https://v3.football.api-sports.io",
        "database_url": "postgresql://user:pass@localhost:5432/prediktia_test",
        "jwt_secret": "unit-test-secret-key-32-chars-min!!",
        "webpay_env": "integration",
        "webpay_commerce_code": "597055555532",
        "webpay_api_key": "579B532A7440BB0C9079DEDCF7D547610A17BE87481CA7D62EC99EC55EB1D1C0",
        "webpay_return_url": "https://api.example.com/payments/webpay/return",
        "frontend_url": "https://app.example.com",
    }
    base.update(overrides)
    return Settings(**base)
