"""Pruebas de permisos y normalización de tiers."""

from __future__ import annotations

import pytest

from app.services.plan_permissions import (
    FREE_HISTORY_LIMIT,
    FREE_VALUE_PICKS_LIMIT,
    PREMIUM_HISTORY_LIMIT,
    VIP_HISTORY_LIMIT,
    can_use_full_value_bets,
    can_use_smart_acca,
    history_cap,
    normalize_tier,
    tier_label,
    value_picks_cap,
)


class TestNormalizeTier:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("free", "free"),
            ("PREMIUM", "premium"),
            ("  vip  ", "vip"),
            ("admin", "admin"),
            (None, "free"),
            ("", "free"),
            ("legacy_plan", "free"),
            ("enterprise", "free"),
        ],
    )
    def test_normalize_tier(self, raw, expected):
        assert normalize_tier(raw) == expected


class TestTierLabel:
    def test_known_labels(self):
        assert tier_label("premium") == "Premium"
        assert tier_label("invalid") == "Free"


class TestPermissions:
    @pytest.mark.parametrize("tier", ["free", None, "unknown"])
    def test_free_cannot_use_premium_features(self, tier):
        assert can_use_smart_acca(tier) is False
        assert can_use_full_value_bets(tier) is False
        assert value_picks_cap(tier) == FREE_VALUE_PICKS_LIMIT

    @pytest.mark.parametrize("tier", ["premium", "vip", "admin"])
    def test_paid_tiers_unlock_features(self, tier):
        assert can_use_smart_acca(tier) is True
        assert can_use_full_value_bets(tier) is True
        assert value_picks_cap(tier) is None


class TestHistoryCap:
    def test_caps_by_tier(self):
        assert history_cap("free", 999) == FREE_HISTORY_LIMIT
        assert history_cap("premium", 999) == PREMIUM_HISTORY_LIMIT
        assert history_cap("vip", 999) == VIP_HISTORY_LIMIT
        assert history_cap("admin", 999) == VIP_HISTORY_LIMIT

    def test_requested_below_minimum_clamped_to_one(self):
        assert history_cap("free", 0) == 1

    def test_requested_within_cap(self):
        assert history_cap("free", 5) == 5
