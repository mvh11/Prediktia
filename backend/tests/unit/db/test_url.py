"""Pruebas de normalización de DATABASE_URL."""

from __future__ import annotations

import pytest

from app.db.url import normalize_database_url


class TestNormalizeDatabaseUrl:
    def test_postgres_scheme(self):
        url = "postgres://user:pass@host/db?sslmode=require"
        assert normalize_database_url(url) == "postgresql+psycopg2://user:pass@host/db?sslmode=require"

    def test_postgresql_scheme(self):
        url = "postgresql://user:pass@host/db"
        assert normalize_database_url(url) == "postgresql+psycopg2://user:pass@host/db"

    def test_already_psycopg2_unchanged_driver(self):
        url = "postgresql+psycopg2://user:pass@host/db"
        assert normalize_database_url(url) == url

    def test_empty_string(self):
        assert normalize_database_url("") == ""
        assert normalize_database_url("   ") == ""

    def test_non_postgres_passthrough(self):
        url = "sqlite:///./local.db"
        assert normalize_database_url(url) == url

    @pytest.mark.parametrize("url", ["not-a-url", "mysql://host/db"])
    def test_other_schemes_without_double_slash(self, url):
        assert normalize_database_url(url) == url
