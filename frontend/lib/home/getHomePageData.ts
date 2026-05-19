import { API_URL } from "@/lib/api";
import {
  buildFixtureValueGroups,
  fetchValueBetsOnce,
  selectPickOfTheDay,
} from "@/lib/valueBets";
import type { ValueBetPick } from "@/lib/valueBets/types";

export type HomeFeaturedSnapshot = {
  fixture_id: number;
  equipo_local: string;
  equipo_visitante: string;
  liga: string;
  fecha: string;
  mercado: string;
  pick: string;
  cuota: number;
  probabilidad: number;
  ev: number;
  ev_pct: number;
  value_grade?: string;
};

export type HomePageData = {
  featured: HomeFeaturedSnapshot | null;
  picks_analyzed: number;
  leagues_monitored: number;
  avg_ev: number | null;
  acca_history_count: number | null;
  value_date: string | null;
  value_source: string | null;
  error: string | null;
};

function snapshotFromHero(hero: ValueBetPick): HomeFeaturedSnapshot {
  return {
    fixture_id: hero.fixture_id,
    equipo_local: hero.equipo_local,
    equipo_visitante: hero.equipo_visitante,
    liga: hero.liga,
    fecha: hero.fecha,
    mercado: hero.mercado,
    pick: hero.pick,
    cuota: hero.cuota,
    probabilidad: hero.probabilidad,
    ev: hero.ev,
    ev_pct: hero.ev * 100,
    value_grade: hero.value_grade,
  };
}

/**
 * Datos públicos para el Home: value-bets del día + pick destacado + conteo ACCA (si la API responde).
 */
export async function getHomePageData(): Promise<HomePageData> {
  const empty: HomePageData = {
    featured: null,
    picks_analyzed: 0,
    leagues_monitored: 0,
    avg_ev: null,
    acca_history_count: null,
    value_date: null,
    value_source: null,
    error: null,
  };

  try {
    const vb = await fetchValueBetsOnce();
    const picks = vb.picks ?? [];
    const groups = buildFixtureValueGroups(picks);
    const editorial = selectPickOfTheDay(groups);
    const fallback =
      editorial ??
      (groups.length
        ? [...groups].sort((a, b) => b.hero.ev - a.hero.ev || b.hero.probabilidad - a.hero.probabilidad)[0]!
        : null);

    const leagues = new Set(picks.map((p) => p.liga).filter(Boolean));
    const avgEv =
      picks.length > 0 ? picks.reduce((s, p) => s + p.ev, 0) / picks.length : null;

    let accaCount: number | null = null;
    try {
      const res = await fetch(`${API_URL}/acca/history?limit=200`, {
        cache: "no-store",
      });
      if (res.ok) {
        const body = (await res.json()) as { items?: unknown[] };
        accaCount = Array.isArray(body.items) ? body.items.length : 0;
      }
    } catch {
      accaCount = null;
    }

    return {
      featured: fallback ? snapshotFromHero(fallback.hero) : null,
      picks_analyzed: vb.picks_count ?? picks.length,
      leagues_monitored: leagues.size,
      avg_ev: avgEv,
      acca_history_count: accaCount,
      value_date: vb.date ?? null,
      value_source: vb.source ?? null,
      error: null,
    };
  } catch (e) {
    return {
      ...empty,
      error: e instanceof Error ? e.message : "fetch_error",
    };
  }
}
