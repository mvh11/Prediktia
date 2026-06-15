import { API_URL } from "@/lib/api";
import { authHeaders } from "./headers";
import type { AuthSession, AuthUser, PaymentHistoryResponse } from "./types";

type AuthErrorBody = {
  detail?: string | { msg?: string }[];
};

function formatAuthError(status: number, body: AuthErrorBody | null): string {
  const detail = body?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail) && detail[0]?.msg) {
    return detail[0].msg;
  }
  if (status === 409) {
    return "Ya existe una cuenta con ese correo.";
  }
  if (status === 401) {
    return "Correo o contraseña incorrectos.";
  }
  if (status === 400) {
    return "No se pudo actualizar el perfil.";
  }
  if (status === 503) {
    return "El servidor no tiene base de datos configurada para login.";
  }
  return "No se pudo completar la autenticación.";
}

async function parseError(res: Response, fallback: string): Promise<string> {
  let body: AuthErrorBody | null = null;
  try {
    body = (await res.json()) as AuthErrorBody;
  } catch {
    body = null;
  }
  if (typeof body?.detail === "string" && body.detail.trim()) {
    return body.detail;
  }
  return fallback;
}

async function postAuth(path: string, payload: Record<string, string>): Promise<AuthSession> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  let body: AuthErrorBody | null = null;
  try {
    body = (await res.json()) as AuthErrorBody;
  } catch {
    body = null;
  }

  if (!res.ok) {
    throw new Error(formatAuthError(res.status, body));
  }

  return body as unknown as AuthSession;
}

export function loginRequest(email: string, password: string): Promise<AuthSession> {
  return postAuth("/auth/login", { email, password });
}

export function registerRequest(
  email: string,
  password: string,
  displayName?: string,
): Promise<AuthSession> {
  const payload: Record<string, string> = { email, password };
  if (displayName?.trim()) {
    payload.display_name = displayName.trim();
  }
  return postAuth("/auth/register", payload);
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  const res = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Sesión expirada.");
  }

  const raw = (await res.json()) as AuthUser & { tier?: string };
  const tier = raw.tier ?? "free";
  return {
    ...raw,
    tier: tier as AuthUser["tier"],
    tier_label: raw.tier_label ?? tier,
  };
}

export async function updateProfileRequest(
  token: string,
  displayName: string,
): Promise<AuthUser> {
  const res = await fetch(`${API_URL}/auth/me`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ display_name: displayName.trim() }),
  });

  if (!res.ok) {
    throw new Error(await parseError(res, "No se pudo actualizar el perfil."));
  }

  const raw = (await res.json()) as AuthUser & { tier?: string };
  const tier = raw.tier ?? "free";
  return {
    ...raw,
    tier: tier as AuthUser["tier"],
    tier_label: raw.tier_label ?? tier,
  };
}

export async function changePasswordRequest(
  token: string,
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const res = await fetch(`${API_URL}/auth/me/password`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });

  if (!res.ok) {
    throw new Error(await parseError(res, "No se pudo cambiar la contraseña."));
  }
}

export async function fetchPaymentHistory(token: string): Promise<PaymentHistoryResponse> {
  const res = await fetch(`${API_URL}/payments/history`, {
    headers: authHeaders(undefined, token),
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("No se pudo cargar el historial de pagos.");
  }

  return (await res.json()) as PaymentHistoryResponse;
}
