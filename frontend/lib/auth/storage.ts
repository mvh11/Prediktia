import type { AuthSession } from "./types";

const STORAGE_KEY = "prediktia.auth";

export function readAuthSession(): AuthSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw) as AuthSession;
  } catch {
    return null;
  }
}

export function writeAuthSession(session: AuthSession): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearAuthSession(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}

export function readAccessToken(): string | null {
  return readAuthSession()?.access_token ?? null;
}
