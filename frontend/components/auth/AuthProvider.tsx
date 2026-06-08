"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { fetchCurrentUser, loginRequest, registerRequest } from "@/lib/auth/api";
import { clearAuthSession, readAuthSession, writeAuthSession } from "@/lib/auth/storage";
import type { AuthUser } from "@/lib/auth/types";

type AuthContextValue = {
  user: AuthUser | null;
  accessToken: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const session = readAuthSession();
      if (!session?.access_token) {
        if (!cancelled) {
          setAccessToken(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const current = await fetchCurrentUser(session.access_token);
        if (!cancelled) {
          setUser(current);
          setAccessToken(session.access_token);
        }
      } catch {
        clearAuthSession();
        if (!cancelled) {
          setUser(null);
          setAccessToken(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const session = await loginRequest(email, password);
    writeAuthSession(session);
    setUser(session.user);
    setAccessToken(session.access_token);
  }, []);

  const register = useCallback(async (email: string, password: string, displayName?: string) => {
    const session = await registerRequest(email, password, displayName);
    writeAuthSession(session);
    setUser(session.user);
    setAccessToken(session.access_token);
  }, []);

  const logout = useCallback(() => {
    clearAuthSession();
    setUser(null);
    setAccessToken(null);
  }, []);

  const value = useMemo(
    () => ({ user, accessToken, isLoading, login, register, logout }),
    [user, accessToken, isLoading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }
  return ctx;
}
