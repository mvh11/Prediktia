import { API_URL } from "@/lib/api";

import { formatMatches } from "./formatMatches";
import type { FormattedMatch } from "./types";

type MatchesApiPayload = {
  raw_fixtures?: unknown;
};

let cache: FormattedMatch[] | null = null;
let inflight: Promise<FormattedMatch[]> | null = null;

/**
 * Una sola petición al backend por proceso: reutiliza caché o la promesa en curso
 * (Strict Mode / navegar entre dev y /matches sin duplicar fetch).
 */
export function fetchFormattedMatchesOnce(): Promise<FormattedMatch[]> {
  if (cache) {
    return Promise.resolve(cache);
  }
  if (inflight) {
    return inflight;
  }

  inflight = (async () => {
    const res = await fetch(`${API_URL}/matches`, { cache: "no-store" });
    if (!res.ok) {
      console.warn(`[matches] HTTP ${res.status} — lista vacía para no romper la demo`);
      cache = [];
      return [];
    }
    const data = (await res.json()) as MatchesApiPayload;
    const clean = formatMatches(data.raw_fixtures ?? []);
    cache = clean;
    return clean;
  })();

  return inflight.finally(() => {
    inflight = null;
  });
}
