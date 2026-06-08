import type { UserTier } from "@/lib/auth/types";

export const TIER_LABELS: Record<UserTier, string> = {
  free: "Free",
  premium: "Premium",
  vip: "VIP",
  admin: "Admin",
};

export const FREE_VALUE_PICKS_LIMIT = 3;
export const FREE_HISTORY_LIMIT = 10;

export function normalizeTier(tier: string | undefined | null): UserTier {
  const t = (tier || "free").toLowerCase();
  if (t === "premium" || t === "vip" || t === "admin") return t;
  return "free";
}

export function tierLabel(tier: UserTier): string {
  return TIER_LABELS[tier];
}

export function canUseSmartAcca(tier: UserTier): boolean {
  return tier === "premium" || tier === "vip" || tier === "admin";
}

export function canUseFullValueBets(tier: UserTier): boolean {
  return tier === "premium" || tier === "vip" || tier === "admin";
}

export function isPaidTier(tier: UserTier): boolean {
  return tier === "premium" || tier === "vip" || tier === "admin";
}

export function tierRank(tier: UserTier): number {
  switch (tier) {
    case "admin":
      return 4;
    case "vip":
      return 3;
    case "premium":
      return 2;
    default:
      return 1;
  }
}
