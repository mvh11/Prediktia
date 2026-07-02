"""Pruebas de formateo de ligas."""

from __future__ import annotations

import pytest

from app.services.league_format import format_league_display


class TestFormatLeagueDisplay:
    def test_name_and_country(self):
        assert format_league_display("Primera División", "Chile") == "Primera División (Chile)"

    def test_country_already_in_name(self):
        assert format_league_display("Primera División Chile", "Chile") == "Primera División Chile"

    def test_empty_country_returns_name_only(self):
        assert format_league_display("Premier League", "") == "Premier League"

    def test_empty_name_returns_country_in_parens(self):
        assert format_league_display("", "Chile") == "— (Chile)"

    @pytest.mark.parametrize("name,country", [("  La Liga  ", "  Spain  ")])
    def test_strips_whitespace(self, name, country):
        result = format_league_display(name, country)
        assert result == "La Liga (Spain)"
