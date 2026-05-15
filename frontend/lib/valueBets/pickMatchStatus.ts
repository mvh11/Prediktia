/**
 * Estado del partido a partir de `estado_partido` (misma lógica que API-Football / matches).
 * Solo para Value Board: ordenación y filtrado client-side.
 */

const LIVE_CODES = new Set([
  "1H",
  "2H",
  "HT",
  "ET",
  "BT",
  "P",
  "SUSP",
  "INT",
  "LIVE",
]);

const FINISHED_CODES = new Set([
  "FT",
  "AET",
  "PEN",
  "PST",
  "CANC",
  "ABD",
  "AWD",
  "WO",
  "AW",
  "AWT",
]);

const UPCOMING_CODES = new Set(["NS", "TBD", "TBA"]);

/** Cancelados / postergados: ocultos por defecto en Value. */
const HIDE_DEFAULT_CODES = new Set(["CANC", "PST"]);

export function statusCodeFromEstado(estado: string): string {
  const t = estado.trim();
  if (t.toLowerCase().startsWith("en juego")) {
    return "LIVE";
  }
  const head = t.split(/[—–-]/)[0]?.trim() ?? t;
  return head.split(/\s+/)[0]?.trim().toUpperCase() ?? "";
}

export function isCancelledOrPostponed(estado: string): boolean {
  return HIDE_DEFAULT_CODES.has(statusCodeFromEstado(estado));
}

/**
 * Orden de visualización: NS/TBD primero, LIVE, FT… y al final CANC/PST.
 */
export function statusSortPriority(estado: string): number {
  const code = statusCodeFromEstado(estado);
  if (HIDE_DEFAULT_CODES.has(code)) {
    return 4;
  }
  if (UPCOMING_CODES.has(code)) {
    return 0;
  }
  if (LIVE_CODES.has(code)) {
    return 1;
  }
  if (FINISHED_CODES.has(code)) {
    return 2;
  }
  return 3;
}

export function isLiveEstado(estado: string): boolean {
  return LIVE_CODES.has(statusCodeFromEstado(estado));
}
