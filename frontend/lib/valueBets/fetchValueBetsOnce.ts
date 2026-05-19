import { API_URL } from "@/lib/api";

import type { ValueBetsResponse } from "./types";

let cache: ValueBetsResponse | null = null;
let inflight: Promise<ValueBetsResponse> | null = null;

/**
 * Una petición a `/value-bets` por sesión de navegación: reutiliza caché en memoria
 * o la promesa en curso (evita doble fetch en Strict Mode / navegación rápida).
 */
export function fetchValueBetsOnce(): Promise<ValueBetsResponse> {
  if (cache) {
    return Promise.resolve(cache);
  }
  if (inflight) {
    return inflight;
  }

  inflight = (async () => {
    const res = await fetch(`${API_URL}/value-bets`, { cache: "no-store" });
    if (!res.ok) {
      console.warn(`[value-bets] HTTP ${res.status} — respuesta vacía para no romper la demo`);
      const empty: ValueBetsResponse = {
        date: "",
        picks_count: 0,
        picks: [],
        upstream_warning: "Backend no disponible temporalmente.",
        cache_stale: false,
      };
      cache = empty;
      return empty;
    }
    const data = (await res.json()) as ValueBetsResponse;
    if (!Array.isArray(data.picks)) {
      data.picks = [];
      data.picks_count = 0;
    }
    cache = data;
    return data;
  })();

  return inflight.finally(() => {
    inflight = null;
  });
}
