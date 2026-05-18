import type { ValueGrade } from "./evPresentation";

/**
 * Contrato del endpoint GET `/value-bets` (backend FastAPI).
 */
export type ValueBetPick = {
  fixture_id: number;
  /** ID competición API-Football; 0 o ausente si no hay upstream. */
  league_id?: number;
  country?: string;
  /** Nombre competición sin país (como API); opcional si solo existe `liga` en UI. */
  league_name?: string;
  /** ID API-Football equipo local (logo en media.api-sports.io). */
  team_home_id?: number;
  /** ID API-Football equipo visitante. */
  team_away_id?: number;
  equipo_local: string;
  equipo_visitante: string;
  liga: string;
  fecha: string;
  estado_partido: string;
  mercado: string;
  pick: string;
  cuota: number;
  probabilidad: number;
  ev: number;
  /** Clase visual: high | good | risky (opcional por compatibilidad con respuestas antiguas). */
  value_grade?: ValueGrade;
};

export type ValueBetsResponse = {
  date: string;
  source?: string;
  picks_count: number;
  picks: ValueBetPick[];
  upstream_warning?: string | null;
  cache_stale?: boolean;
};
