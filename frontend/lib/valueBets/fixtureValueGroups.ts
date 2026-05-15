import { classifyValuePick } from "./classifyValuePick";
import { computeRankScore } from "./rankScore";
import type { ValueBetPick } from "./types";

import type { ValueGrade } from "./evPresentation";

const MERCADO_ORDER: Record<string, number> = {
  "1X2": 0,
  "Doble oportunidad": 1,
  "Total goles": 2,
  "Ambos marcan": 3,
};

function foldPick(pick: string): string {
  return pick
    .normalize("NFD")
    .replace(/\p{M}+/gu, "")
    .toLowerCase()
    .trim();
}

function oneX2OutcomeOrder(pick: ValueBetPick): number {
  if (pick.mercado !== "1X2") {
    return 0;
  }
  const pk = foldPick(pick.pick);
  if (pk === "victoria local") {
    return 0;
  }
  if (pk === "empate") {
    return 1;
  }
  if (pk === "victoria visitante") {
    return 2;
  }
  return 3;
}

function compareHero(a: ValueBetPick, b: ValueBetPick): number {
  const ra = computeRankScore(a);
  const rb = computeRankScore(b);
  if (Math.abs(ra - rb) > 1e-4) {
    return rb - ra;
  }
  return b.ev - a.ev;
}

/** Orden estable para el panel expandido: mercado → 1X2 local/X/visitante → score. */
export function sortPicksForFixtureDetail(a: ValueBetPick, b: ValueBetPick): number {
  const oa = MERCADO_ORDER[a.mercado] ?? 99;
  const ob = MERCADO_ORDER[b.mercado] ?? 99;
  if (oa !== ob) {
    return oa - ob;
  }
  if (a.mercado === "1X2" && b.mercado === "1X2") {
    const ox = oneX2OutcomeOrder(a) - oneX2OutcomeOrder(b);
    if (ox !== 0) {
      return ox;
    }
  }
  return compareHero(a, b);
}

export function pickHeroForFixture(picks: ValueBetPick[]): ValueBetPick {
  return [...picks].sort(compareHero)[0]!;
}

export function groupPicksByFixture(picks: ValueBetPick[]): Map<number, ValueBetPick[]> {
  const m = new Map<number, ValueBetPick[]>();
  for (const p of picks) {
    const arr = m.get(p.fixture_id) ?? [];
    arr.push(p);
    m.set(p.fixture_id, arr);
  }
  return m;
}

export type FixtureValueGroup = {
  fixture_id: number;
  picks: ValueBetPick[];
  hero: ValueBetPick;
  heroGrade: ValueGrade;
};

export function buildFixtureValueGroups(picks: ValueBetPick[]): FixtureValueGroup[] {
  const map = groupPicksByFixture(picks);
  return [...map.entries()].map(([fixture_id, plist]) => {
    const hero = pickHeroForFixture(plist);
    const picks = [...plist].sort(sortPicksForFixtureDetail);
    return {
      fixture_id,
      picks,
      hero,
      heroGrade: classifyValuePick(hero),
    };
  });
}
