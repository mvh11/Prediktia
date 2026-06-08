import { readAccessToken } from "./storage";

export function authHeaders(extra?: HeadersInit, accessToken?: string | null): HeadersInit {
  const token = accessToken ?? readAccessToken();
  if (!token) {
    return extra ?? {};
  }
  return {
    ...extra,
    Authorization: `Bearer ${token}`,
  };
}
