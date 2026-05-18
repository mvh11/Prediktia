"""Formato unificado de competición: `Nombre (País)`."""

from __future__ import annotations


def format_league_display(league_name: str, country: str) -> str:
    name = (league_name or "").strip() or "—"
    c = (country or "").strip()
    if not c:
        return name
    nl = name.lower()
    cl = c.lower()
    if cl in nl:
        return name
    return f"{name} ({c})"
