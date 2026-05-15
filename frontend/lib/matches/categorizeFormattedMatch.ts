import type { FormattedMatch } from "./types";

export type MatchBucket = "live" | "upcoming" | "finished";

/** Códigos cortos habituales de API-Football (status.short). */
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

function statusToken(estado: string): string {
  const t = estado.trim();
  if (t.toLowerCase().startsWith("en juego")) {
    return "LIVE";
  }
  const head = t.split(/[—–-]/)[0]?.trim() ?? t;
  return head.split(/\s+/)[0]?.trim().toUpperCase() ?? "";
}

export function categorizeFormattedMatch(m: FormattedMatch): MatchBucket {
  const code = statusToken(m.estado_partido);
  if (LIVE_CODES.has(code)) {
    return "live";
  }
  if (FINISHED_CODES.has(code)) {
    return "finished";
  }
  if (UPCOMING_CODES.has(code)) {
    return "upcoming";
  }
  if (m.goles_local !== null && m.goles_visitante !== null) {
    return "finished";
  }
  return "upcoming";
}

export function partitionMatchesByBucket(matches: FormattedMatch[]): {
  live: FormattedMatch[];
  upcoming: FormattedMatch[];
  finished: FormattedMatch[];
} {
  const live: FormattedMatch[] = [];
  const upcoming: FormattedMatch[] = [];
  const finished: FormattedMatch[] = [];
  for (const m of matches) {
    const b = categorizeFormattedMatch(m);
    if (b === "live") {
      live.push(m);
    } else if (b === "finished") {
      finished.push(m);
    } else {
      upcoming.push(m);
    }
  }
  return { live, upcoming, finished };
}
