/**
 * Orden editorial del feed: región → prestigio → score → liquidez → EV.
 * Prioriza Europa top, luego LATAM principal, luego secundarias / ROW.
 */

import { computeRankScore } from "./rankScore";
import { statusSortPriority } from "./pickMatchStatus";
import type { ValueBetPick } from "./types";

import type { FixtureValueGroup } from "./fixtureValueGroups";
import {
  combinedLeagueFold,
  foldText,
  getLeagueTierForPick,
  leaguePrestigeSortKey,
} from "./leagueTiers";

/** Europa top: Big 5 + copas UEFA + selecciones top. */
const EU_TOP_IDS: ReadonlySet<number> = new Set([39, 140, 135, 78, 61, 2, 3, 848, 1, 4]);

/**
 * LATAM principal (Prediktia). IDs API-Football v3 — revisar en dashboard si cambian.
 */
const LATAM_TOP_IDS: ReadonlySet<number> = new Set([
  265, // Chile Primera
  128, // Argentina LPF
  71, // Brasileirão A
  262, // Liga MX
  239, // Colombia Primera A
  268, // Uruguay
  281, // Perú Liga 1
  242, // Ecuador LigaPro
  13, // Libertadores
  11, // Sudamericana
]);

/**
 * Europa secundaria, MLS, Arabia, Championship y similares (no “random ROW” pero por debajo de LATAM top).
 */
const SECONDARY_TIER_IDS: ReadonlySet<number> = new Set([
  40, 41, 42, // Championship / L1 / L2
  253, // MLS
  307, // Saudi Pro
  88, // Eredivisie
  94, // Portugal
  144, // Bélgica
  179, // Escocia
  203, // Turquía
  197, // Grecia
  207, // Suiza
  218, // Austria
  235, // Rusia
  136, 141, // Serie B / LaLiga2
  79, 62, // 2.Bundesliga / Ligue 2
  72, // Brasil Serie B
  266, 263, // Chile B / MX expansión
]);

const LATAM_TOP_STRING_PAIRS: readonly [string, string][] = [
  ["chile", "primera"],
  ["argentina", "liga"],
  ["argentina", "lpf"],
  ["argentina", "primera"],
  ["brazil", "brasileir"],
  ["brasil", "brasileir"],
  ["mexico", "liga mx"],
  ["méxico", "liga mx"],
  ["colombia", "primera"],
  ["colombia", "betplay"],
  ["uruguay", "primera"],
  ["peru", "liga 1"],
  ["perú", "liga 1"],
  ["ecuador", "liga pro"],
];

const POPULAR_CLUB_NEEDLES: readonly string[] = [
  "colo-colo",
  "colo colo",
  "universidad de chile",
  "universidad chile",
  "u. de chile",
  " u de chile",
  "coquimbo unido",
  "coquimbo",
  "river plate",
  "boca juniors",
  "boca j",
  "flamengo",
  "palmeiras",
  "chivas",
  "guadalajara",
  "club america",
  "club américa",
  "cf america",
  "cf américa",
  "club de futbol america",
  "club de fútbol américa",
];

function latamTopByString(pick: ValueBetPick): boolean {
  const x = combinedLeagueFold(pick);
  if (x.includes("libertadores") || x.includes("sudamericana")) {
    return true;
  }
  return LATAM_TOP_STRING_PAIRS.some(([a, b]) => x.includes(a) && x.includes(b));
}

function isLatamTopFixture(pick: ValueBetPick): boolean {
  const id = pick.league_id ?? 0;
  if (LATAM_TOP_IDS.has(id)) {
    return true;
  }
  if (getLeagueTierForPick(pick) === "D") {
    return false;
  }
  return latamTopByString(pick);
}

/**
 * Peso editorial por región / nivel de competición (mayor = más arriba en el feed).
 * 100 Europa top · 85 LATAM top · 60 secundarias / MLS / Arabia / Championship · 30 resto.
 */
export function editorialRegionWeight(pick: ValueBetPick): number {
  const id = pick.league_id ?? 0;
  if (EU_TOP_IDS.has(id)) {
    return 100;
  }
  if (isLatamTopFixture(pick)) {
    return 85;
  }
  if (SECONDARY_TIER_IDS.has(id)) {
    return 60;
  }
  const lt = getLeagueTierForPick(pick);
  if (lt === "S" || lt === "A") {
    return 60;
  }
  if (lt === "B") {
    return 55;
  }
  return 30;
}

/** Prestigio numérico alto = mejor (para orden DESC). */
export function editorialPrestigeScore(pick: ValueBetPick): number {
  return 100 - leaguePrestigeSortKey(pick);
}

/** Boost por clubes icónicos (Prediktia / audiencia LATAM). */
export function popularClubBoost(pick: ValueBetPick): number {
  const b = foldText(`${pick.equipo_local} ${pick.equipo_visitante}`);
  let n = 0;
  for (const needle of POPULAR_CLUB_NEEDLES) {
    if (b.includes(needle)) {
      n += 1;
    }
  }
  return Math.min(26, n * 9);
}

/** Pick score editorial = rank base + clubes populares. */
export function editorialPickScore(pick: ValueBetPick): number {
  return computeRankScore(pick) + popularClubBoost(pick);
}

/**
 * Liquidez proxy para ordenar (mayor = cuota más “mainline” / creíble).
 */
export function editorialLiquidityScore(pick: ValueBetPick): number {
  const o = pick.cuota;
  if (o >= 1.42 && o <= 2.55) {
    return 95 - Math.abs(o - 1.92) * 22;
  }
  if (o < 1.42) {
    return 55;
  }
  if (o <= 3.15) {
    return 48 - (o - 2.55) * 8;
  }
  return 22;
}

/**
 * Regla dura: LATAM top con EV ≥ 5% no pierde frente a ROW (peso 30) aunque el score sea parecido.
 */
function latamTopEvFloor(a: FixtureValueGroup, b: FixtureValueGroup): number | null {
  const wb = editorialRegionWeight(b.hero);
  const wa = editorialRegionWeight(a.hero);
  const aLatamStrong = isLatamTopFixture(a.hero) && a.hero.ev >= 0.05;
  const bLatamStrong = isLatamTopFixture(b.hero) && b.hero.ev >= 0.05;
  if (aLatamStrong && wb <= 30) {
    return -1;
  }
  if (bLatamStrong && wa <= 30) {
    return 1;
  }
  return null;
}

/**
 * Comparador principal del feed (partidos).
 * Orden: status → región → prestigio → pick score → liquidez → EV.
 */
export function compareFixtureGroupsEditorial(a: FixtureValueGroup, b: FixtureValueGroup): number {
  const da = a.hero.estado_partido;
  const db = b.hero.estado_partido;
  const sa0 = statusSortPriority(da);
  const sb0 = statusSortPriority(db);
  if (sa0 !== sb0) {
    return sa0 - sb0;
  }

  const floor = latamTopEvFloor(a, b);
  if (floor !== null) {
    return floor;
  }

  const wa = editorialRegionWeight(a.hero);
  const wb = editorialRegionWeight(b.hero);
  if (wa !== wb) {
    return wb - wa;
  }

  const pa = editorialPrestigeScore(a.hero);
  const pb = editorialPrestigeScore(b.hero);
  if (pa !== pb) {
    return pb - pa;
  }

  const pka = editorialPickScore(a.hero);
  const pkb = editorialPickScore(b.hero);
  if (Math.abs(pka - pkb) > 1e-3) {
    return pkb - pka;
  }

  const la = editorialLiquidityScore(a.hero);
  const lb = editorialLiquidityScore(b.hero);
  if (Math.abs(la - lb) > 1e-3) {
    return lb - la;
  }

  return b.hero.ev - a.hero.ev;
}
