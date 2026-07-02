"""Pruebas de extracción de cuotas bookmaker."""

from __future__ import annotations

from app.services.acca_odds import extract_market_odds, _parse_odd, _pick_from_values


class TestParseOdd:
    def test_valid_float(self):
        assert _parse_odd(2.05) == 2.05

    def test_invalid_low_odd(self):
        assert _parse_odd(1.0) is None

    def test_string_odd(self):
        assert _parse_odd("3,50") == 3.5


class TestPickFromValues:
    def test_home_away_draw(self):
        values = [
            {"value": "Home", "odd": "2.10"},
            {"value": "Draw", "odd": "3.40"},
            {"value": "Away", "odd": "3.80"},
        ]
        picked = _pick_from_values(values, "Arsenal", "Chelsea", draw="draw")
        assert picked["home"] == 2.10
        assert picked["draw"] == 3.40
        assert picked["away"] == 3.80


class TestExtractMarketOdds:
    def test_extracts_1x2_and_over_under(self):
        payload = {
            "response": [
                {
                    "bookmakers": [
                        {
                            "bets": [
                                {
                                    "name": "Match Winner",
                                    "values": [
                                        {"value": "Home", "odd": 1.95},
                                        {"value": "Draw", "odd": 3.5},
                                        {"value": "Away", "odd": 4.2},
                                    ],
                                },
                                {
                                    "name": "Goals Over/Under 2.5",
                                    "values": [
                                        {"value": "Over 2.5", "odd": 1.85},
                                        {"value": "Under 2.5", "odd": 2.0},
                                    ],
                                },
                            ]
                        }
                    ]
                }
            ]
        }
        markets = extract_market_odds(payload, "Arsenal", "Chelsea")
        assert "1x2" in markets
        assert markets["1x2"]["home"] == 1.95
        assert "ou_25" in markets
        assert markets["ou_25"]["over_25"] == 1.85

    def test_empty_response(self):
        assert extract_market_odds({}, "A", "B") == {}
        assert extract_market_odds({"response": []}, "A", "B") == {}
