/**
 * URL base del backend FastAPI (Render en producción, local en desarrollo).
 * Definir en Vercel / .env.local:
 *   NEXT_PUBLIC_API_URL=https://prediktia-backend.onrender.com
 */
const PRODUCTION_DEFAULT = "https://prediktia-backend.onrender.com";

function trimTrailingSlash(url: string): string {
  return url.replace(/\/$/, "");
}

function readApiUrlFromEnv(): string | undefined {
  const primary = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (primary) {
    return trimTrailingSlash(primary);
  }
  const legacy = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();
  if (legacy) {
    return trimTrailingSlash(legacy);
  }
  return undefined;
}

export const API_URL = readApiUrlFromEnv() ?? PRODUCTION_DEFAULT;

/** Alias histórico usado por módulos de partidos. */
export const MATCHES_BASE_URL = API_URL;
