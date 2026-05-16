import { MATCHES_BASE_URL } from "@/lib/matches";

import type { AccaRiskLevel, SmartAccaResponse } from "./types";

export async function fetchSmartAcca(
  risk: AccaRiskLevel,
  options?: { date?: string; fetchOdds?: boolean },
): Promise<SmartAccaResponse> {
  const params = new URLSearchParams({ risk });
  if (options?.date) {
    params.set("date", options.date);
  }
  if (options?.fetchOdds === false) {
    params.set("fetch_odds", "false");
  }

  const res = await fetch(`${MATCHES_BASE_URL}/acca?${params.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} al llamar /acca`);
  }
  const data = (await res.json()) as SmartAccaResponse;
  if (!Array.isArray(data.picks)) {
    throw new Error("Respuesta /acca inválida");
  }
  return data;
}
