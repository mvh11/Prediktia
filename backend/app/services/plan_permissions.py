"""Permisos por plan (tier) de usuario — preparado para suscripciones / Transbank."""

from __future__ import annotations

VALID_TIERS = frozenset({"free", "premium", "vip", "admin"})

TIER_LABELS: dict[str, str] = {
    "free": "Free",
    "premium": "Premium",
    "vip": "VIP",
    "admin": "Admin",
}

FREE_VALUE_PICKS_LIMIT = 3
FREE_HISTORY_LIMIT = 10
PREMIUM_HISTORY_LIMIT = 100
VIP_HISTORY_LIMIT = 200


def normalize_tier(tier: str | None) -> str:
    """Usuarios legacy o valores inválidos → free."""
    raw = (tier or "free").strip().lower()
    if raw in VALID_TIERS:
        return raw
    return "free"


def tier_label(tier: str | None) -> str:
    return TIER_LABELS.get(normalize_tier(tier), "Free")


def can_use_smart_acca(tier: str | None) -> bool:
    return normalize_tier(tier) in ("premium", "vip", "admin")


def can_use_full_value_bets(tier: str | None) -> bool:
    return normalize_tier(tier) in ("premium", "vip", "admin")


def value_picks_cap(tier: str | None) -> int | None:
    """None = sin límite; int = máximo de picks devueltos."""
    if can_use_full_value_bets(tier):
        return None
    return FREE_VALUE_PICKS_LIMIT


def history_cap(tier: str | None, requested: int) -> int:
    t = normalize_tier(tier)
    if t in ("vip", "admin"):
        cap = VIP_HISTORY_LIMIT
    elif t == "premium":
        cap = PREMIUM_HISTORY_LIMIT
    else:
        cap = FREE_HISTORY_LIMIT
    return max(1, min(requested, cap))
