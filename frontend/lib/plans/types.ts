import type { UserTier } from "@/lib/auth/types";

export type PlanId = UserTier;

export type PlanFeature = {
  label: string;
  included: boolean;
  highlight?: boolean;
};

export type PlanDefinition = {
  id: PlanId;
  name: string;
  tagline: string;
  priceLabel: string;
  priceNote: string;
  badge?: string;
  gradient: string;
  glow: string;
  ring: string;
  icon: string;
  features: PlanFeature[];
  cta: string;
  ctaVariant: "free" | "premium" | "vip";
};
