import { MATCHES_BASE_URL } from "@/lib/matches";

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
    const res = await fetch(`${MATCHES_BASE_URL}/value-bets`, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status} al llamar ${MATCHES_BASE_URL}/value-bets`);
    }
    const data = (await res.json()) as ValueBetsResponse;
    if (!Array.isArray(data.picks)) {
      throw new Error("Respuesta inválida: falta picks[]");
    }
    cache = data;
    return data;
  })();

  return inflight.finally(() => {
    inflight = null;
  });
}
