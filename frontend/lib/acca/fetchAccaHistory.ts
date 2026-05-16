import { MATCHES_BASE_URL } from "@/lib/matches";

import type { AccaHistoryListResponse } from "./types";

export async function fetchAccaHistory(limit = 30): Promise<AccaHistoryListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  const res = await fetch(`${MATCHES_BASE_URL}/acca/history?${params.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} al llamar /acca/history`);
  }
  const data = (await res.json()) as AccaHistoryListResponse;
  if (!Array.isArray(data.items)) {
    throw new Error("Respuesta /acca/history inválida");
  }
  return data;
}
