/**
 * Formato estable que consume el frontend (independiente del naming interno de la API).
 */
export interface FormattedMatch {
  fixture_id: number;
  fecha: string;
  liga: string;
  pais: string;
  equipo_local: string;
  equipo_visitante: string;
  goles_local: number | null;
  goles_visitante: number | null;
  estado_partido: string;
}

/**
 * Subconjunto tipado del item `response[]` de API-Football (fixtures).
 * Los campos son opcionales porque la API puede variar o faltar datos en vivo.
 */
export interface ApiFootballFixtureItem {
  fixture?: {
    id?: number;
    date?: string;
    status?: {
      long?: string | null;
      short?: string | null;
      elapsed?: number | null;
    };
  };
  league?: {
    name?: string | null;
    country?: string | null;
  };
  teams?: {
    home?: { name?: string | null };
    away?: { name?: string | null };
  };
  goals?: {
    home?: number | null;
    away?: number | null;
  };
}

export type FormatMatchesOptions = {
  /**
   * Si es true, el primer elemento inválido lanza error.
   * Si es false (por defecto), se omiten filas inválidas.
   */
  strict?: boolean;
  /**
   * Callback opcional para telemetría o depuración cuando se omite una fila.
   */
  onSkip?: (info: { index: number; reason: string }) => void;
};
