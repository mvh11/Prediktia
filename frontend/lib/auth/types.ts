export type UserTier = "free" | "premium" | "vip" | "admin";

export type AuthUser = {
  id: number;
  email: string;
  display_name: string;
  tier: UserTier;
  tier_label?: string;
};

export type AuthSession = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};
