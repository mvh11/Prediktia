import { MATCHES_BASE_URL } from "@/lib/matches";

import type { AccaHistoryItem, AccaHistoryListResponse } from "./types";

function normalizeItem(raw: Record<string, unknown>): AccaHistoryItem {
  const accaId = String(raw.acca_id ?? raw.id ?? "");
  const totalEv = Number(raw.total_ev ?? raw.combined_ev_pct ?? 0);
  const picksCount = Number(raw.picks_count ?? raw.pick_count ?? 0);
  const conf = Number(raw.confidence ?? raw.confidence_score ?? 0);
  return {
    id: accaId,
    acca_id: accaId,
    created_at: String(raw.created_at ?? ""),
    date: String(raw.date ?? ""),
    risk: String(raw.risk ?? ""),
    risk_label: String(raw.risk_label ?? raw.risk ?? ""),
    total_odds: Number(raw.total_odds ?? 1),
    total_ev: totalEv,
    combined_ev_pct: totalEv,
    confidence: conf,
    confidence_score: conf,
    picks_count: picksCount,
    pick_count: picksCount,
    status: "pending",
  };
}

export async function fetchAccaHistory(limit = 30): Promise<AccaHistoryListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  const res = await fetch(`${MATCHES_BASE_URL}/acca/history?${params.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error("history_unavailable");
  }
  const data = (await res.json()) as {
    items?: unknown[];
    database_configured?: boolean;
  };
  const items = Array.isArray(data.items)
    ? data.items
        .filter((x): x is Record<string, unknown> => typeof x === "object" && x !== null)
        .map(normalizeItem)
        .filter((x) => x.acca_id.length > 0)
    : [];
  return {
    items,
    database_configured: Boolean(data.database_configured),
  };
}
