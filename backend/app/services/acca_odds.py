"""
Extracción de cuotas bookmaker desde API-Football /odds.
"""

from __future__ import annotations

from typing import Any


def _fold(s: str) -> str:
    return s.lower().strip()


def _parse_odd(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        o = float(value)
        return o if o >= 1.01 else None
    if isinstance(value, str):
        try:
            o = float(value.replace(",", "."))
            return o if o >= 1.01 else None
        except ValueError:
            return None
    return None


def _bet_name_matches(name: str, needles: tuple[str, ...]) -> bool:
    n = _fold(name)
    return any(needle in n for needle in needles)


def _pick_from_values(values: Any, home: str, away: str, draw: str | None = None) -> dict[str, float]:
    out: dict[str, float] = {}
    if not isinstance(values, list):
        return out
    h = _fold(home)
    a = _fold(away)
    for v in values:
        if not isinstance(v, dict):
            continue
        label = _fold(str(v.get("value") or ""))
        odd = _parse_odd(v.get("odd"))
        if odd is None:
            continue
        if label in ("home", "1", h) or h in label:
            out["home"] = odd
        elif label in ("away", "2", a) or a in label:
            out["away"] = odd
        elif draw and (label in ("draw", "x", "empate") or "draw" in label):
            out["draw"] = odd
        elif label == "yes" or label == "si" or label == "sí":
            out["yes"] = odd
        elif label == "no":
            out["no"] = odd
        elif "over" in label and "2.5" in label.replace(" ", ""):
            out["over_25"] = odd
        elif "under" in label and "2.5" in label.replace(" ", ""):
            out["under_25"] = odd
        elif label in ("1x", "home/draw", "home or draw"):
            out["1x"] = odd
        elif label in ("x2", "draw/away", "draw or away"):
            out["x2"] = odd
        elif label in ("12", "home/away", "home or away"):
            out["12"] = odd
    return out


def extract_market_odds(odds_payload: dict[str, Any], home: str, away: str) -> dict[str, dict[str, float]]:
    """
    Devuelve mapa mercado → {selection_key: cuota} usando el primer bookmaker con datos.
    """
    response = odds_payload.get("response")
    if not isinstance(response, list) or not response:
        return {}

    block = response[0] if isinstance(response[0], dict) else {}
    bookmakers = block.get("bookmakers")
    if not isinstance(bookmakers, list):
        return {}

    markets: dict[str, dict[str, float]] = {}

    for bm in bookmakers:
        if not isinstance(bm, dict):
            continue
        bets = bm.get("bets")
        if not isinstance(bets, list):
            continue
        for bet in bets:
            if not isinstance(bet, dict):
                continue
            name = str(bet.get("name") or "")
            values = bet.get("values")
            if _bet_name_matches(name, ("match winner", "1x2", "full time result", "winner")):
                picked = _pick_from_values(values, home, away, draw="draw")
                if picked:
                    markets.setdefault("1x2", {}).update(picked)
            elif _bet_name_matches(name, ("over/under", "goals over", "total goals")) and "2.5" in _fold(name):
                picked = _pick_from_values(values, home, away)
                if "over_25" in picked or "under_25" in picked:
                    markets.setdefault("ou_25", {}).update(picked)
            elif _bet_name_matches(name, ("both teams", "btts", "both teams to score")):
                picked = _pick_from_values(values, home, away)
                if "yes" in picked or "no" in picked:
                    markets.setdefault("btts", {}).update(
                        {"yes": picked.get("yes", 0), "no": picked.get("no", 0)}
                    )
            elif _bet_name_matches(name, ("double chance",)):
                picked = _pick_from_values(values, home, away)
                if picked:
                    markets.setdefault("dc", {}).update(picked)

        if markets:
            break

    return {k: {sk: sv for sk, sv in v.items() if sv >= 1.01} for k, v in markets.items() if v}
