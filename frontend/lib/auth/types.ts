export type UserTier = "free" | "premium" | "vip";

export type AuthUser = {
  id: number;
  email: string;
  display_name: string;
  tier: UserTier;
};

export type AuthSession = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};
