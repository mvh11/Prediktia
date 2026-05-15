import { isDrawPick } from "./classifyValuePick";
import { compareFixtureGroupsEditorial } from "./editorialFeedSort";
import type { FixtureValueGroup } from "./fixtureValueGroups";
import {
  getLeagueTierForPick,
  isLatamEditorialContext,
  LATAM_EDITORIAL_IDS,
  TOP_EU_PRESTIGE_IDS,
} from "./leagueTiers";
import { computeRankScore } from "./rankScore";

/** Puntuación interna para elegir el partido destacado (no es el mismo rank que la lista). */
export function pickOfTheDayScore(group: FixtureValueGroup): number {
  const h = group.hero;
  let s = computeRankScore(h);
  const id = h.league_id ?? 0;
  if (TOP_EU_PRESTIGE_IDS.has(id)) {
    s += 34;
  } else if (LATAM_EDITORIAL_IDS.has(id) || isLatamEditorialContext(h)) {
    s += 28;
  } else if (getLeagueTierForPick(h) === "S") {
    s += 16;
  }
  return s;
}

export function isPickOfTheDayCandidate(group: FixtureValueGroup): boolean {
  const h = group.hero;
  const id = h.league_id ?? 0;
  const mercadoOk =
    (h.mercado === "1X2" && !isDrawPick(h)) || h.mercado === "Doble oportunidad";
  const oddsOk = h.cuota >= 1.46 && h.cuota <= 2.72;
  const evOk = h.ev >= 0.04 && h.ev <= 0.118;
  const lt = getLeagueTierForPick(h);
  const leagueOk =
    TOP_EU_PRESTIGE_IDS.has(id) ||
    LATAM_EDITORIAL_IDS.has(id) ||
    isLatamEditorialContext(h) ||
    lt === "S" ||
    lt === "A";
  return mercadoOk && oddsOk && evOk && leagueOk;
}

export function selectPickOfTheDay(groups: FixtureValueGroup[]): FixtureValueGroup | null {
  const cand = groups.filter(isPickOfTheDayCandidate);
  if (cand.length === 0) {
    return null;
  }
  return [...cand].sort((a, b) => {
    const ed = compareFixtureGroupsEditorial(a, b);
    if (ed !== 0) {
      return ed;
    }
    const sa = pickOfTheDayScore(a);
    const sb = pickOfTheDayScore(b);
    if (Math.abs(sa - sb) > 1e-4) {
      return sb - sa;
    }
    return b.hero.ev - a.hero.ev;
  })[0]!;
}
