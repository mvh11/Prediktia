export type AccaRiskLevel = "low" | "medium" | "high" | "extreme";

export type AccaPick = {
  fixture_id: number;
  liga: string;
  equipo_local: string;
  equipo_visitante: string;
  fecha: string;
  kickoff_in_minutes?: number | null;
  mercado: string;
  pick: string;
  cuota: number;
  probabilidad: number;
  ev: number;
  ev_pct: number;
  edge_pct: number;
  confidence_pct: number;
  implied_probability: number;
  odds_source: "bookmaker" | "synthetic";
};

export type SmartAccaResponse = {
  date: string;
  model_version: string;
  risk: AccaRiskLevel;
  risk_label: string;
  profile: {
    min_picks: number;
    max_picks: number;
    target_odds_range: string;
  };
  picks: AccaPick[];
  pick_count: number;
  total_odds: number;
  combined_probability: number;
  combined_ev: number;
  combined_ev_pct: number;
  confidence_score: number;
  risk_score: number;
  volatility_score: number;
  meta: {
    candidates_pool_size: number;
    eligible_after_filters: number;
    bookmaker_odds_picks: number;
    independence_assumption: string;
    fetch_odds: boolean;
    fixtures_upstream_total?: number;
    fixtures_after_schedule_filter?: number;
    schedule_discard_reasons?: Record<string, number>;
    fixtures_source?: string;
    requested_date?: string;
    resolved_date?: string;
    auto_shifted_date?: boolean;
  };
  message?: string | null;
  acca_id?: string | null;
};

export type AccaSettlementStatus = "pending" | "won" | "lost";

export type AccaHistoryItem = {
  acca_id: string;
  date: string;
  risk: string;
  risk_label: string;
  total_odds: number;
  combined_ev_pct: number;
  confidence_score: number;
  pick_count: number;
  created_at: string;
  status: AccaSettlementStatus;
  result?: string | null;
  roi?: number | null;
  model_version: string;
};

export type AccaHistoryListResponse = {
  items: AccaHistoryItem[];
  database_configured: boolean;
};
