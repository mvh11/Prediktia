/**
 * Tiers S→D usando league_id (API-Football), país + nombre de competición y texto de UI.
 * Evita que "Premier League" genérica herede reputación de la EPL sin contexto.
 */

import type { ValueBetPick } from "./types";

export type LeagueTierCode = "S" | "A" | "B" | "C" | "D";

export type PickLeagueContext = Pick<ValueBetPick, "liga" | "league_id" | "country" | "league_name">;

export function foldText(s: string): string {
  return s
    .normalize("NFD")
    .replace(/\p{M}+/gu, "")
    .toLowerCase()
    .trim();
}

/** Quita sufijo " (País)" del texto de UI para recuperar el nombre base si falta league_name. */
export function stripLeagueCountrySuffix(liga: string): string {
  return liga.replace(/\s*\([^)]+\)\s*$/u, "").trim();
}

export function effectiveLeagueName(pick: PickLeagueContext): string {
  const raw = pick.league_name?.trim();
  if (raw) {
    return raw;
  }
  return stripLeagueCountrySuffix(pick.liga) || pick.liga;
}

export function effectiveCountry(pick: PickLeagueContext): string {
  return (pick.country ?? "").trim();
}

/** Cadena unificada país + competición para heurísticas (no usar solo el nombre corto). */
export function combinedLeagueFold(pick: PickLeagueContext): string {
  const c = foldText(effectiveCountry(pick));
  const n = foldText(effectiveLeagueName(pick));
  if (c && n) {
    return `${c} ${n}`.trim();
  }
  return n || c;
}

/**
 * IDs API-Football v3 (dashboard). Desambigua competiciones homónimas.
 * @see https://www.api-football.com/documentation-v3
 */
const LEAGUE_IDS_TIER_S: ReadonlySet<number> = new Set([
  39, // England Premier League
  140, // Spain La Liga
  135, // Italy Serie A
  78, // Germany Bundesliga
  61, // France Ligue 1
  71, // Brazil Serie A (Brasileirão)
  262, // Mexico Liga MX
  265, // Chile Primera
  128, // Argentina Liga Profesional
  253, // USA MLS
  2, // UEFA Champions League
  3, // UEFA Europa League
  848, // UEFA Conference League
  13, // Copa Libertadores
]);

const LEAGUE_IDS_TIER_A: ReadonlySet<number> = new Set([
  88, // Netherlands Eredivisie
  94, // Portugal Primeira Liga
  179, // Scotland Premiership
  144, // Belgium Pro League
  203, // Turkey Süper Lig
  98, // Japan J1 League
  292, // Korea K League 1
  169, // China Super League
  307, // Saudi Pro League
  197, // Greece Super League
  207, // Switzerland Super League
  218, // Austria Bundesliga
  235, // Russia Premier League
  1, // World Cup
  4, // EURO
]);

const LEAGUE_IDS_TIER_B: ReadonlySet<number> = new Set([
  40, // Championship
  41, // League One
  42, // League Two
  136, // Italy Serie B
  141, // Spain La Liga 2
  79, // 2. Bundesliga
  62, // Ligue 2
  72, // Brazil Serie B
  266, // Chile Primera B
  263, // Mexico Expansion
]);

/** Femenino top: no caer en Tier D genérico. */
const WOMEN_TIER_A_ALLOW: readonly string[] = [
  "women super league",
  "womens super league",
  "barclays wsl",
  "nwsl",
  "national womens soccer",
  "frauen-bundesliga",
  "division 1 feminine",
  "ligue 1 feminine",
  "serie a women",
];

/** Señales Tier D (juveniles, reservas, regionales, femenino random, divisiones basura). */
const TIER_D_SIGNALS: readonly string[] = [
  "u19",
  "u20",
  "u21",
  "u22",
  "u23",
  "sub-19",
  "sub 19",
  "sub-20",
  "sub 20",
  "sub-21",
  "juvenil",
  "juvenile",
  "youth",
  "academy",
  "reserva",
  "reserve",
  "b team",
  " ii",
  " iii",
  "liga iii",
  "tercera",
  "cuarta",
  "4th division",
  "5th division",
  "regional",
  "amateur",
  "district",
  "girls",
  "niños",
  "niñas",
  "femenino u",
  "women u",
  "ladies",
];

/** Segundas, copas nacionales, expansion — encajan en país+nombre o id. */
const TIER_B: readonly string[] = [
  "championship",
  "league one",
  "league two",
  "segunda division",
  "laliga 2",
  "laliga hypermotion",
  "serie b",
  "bundesliga 2",
  "2. bundesliga",
  "ligue 2",
  "eredivisie eerste",
  "brasileiro serie b",
  "serie b brazil",
  "usl championship",
  "usl league one",
  "liga de expansion",
  "mx expansion",
  "primera nacional",
  "primera b chile",
  "primera b",
  "segunda division chile",
  "ascenso mx",
  "league cup",
  "carabao cup",
  "fa cup",
  "copa del rey",
  "copa italia",
  "dfb-pokal",
  "coupe de france",
];

const TIER_A_STRINGS: readonly string[] = [
  "eredivisie",
  "primeira liga",
  "liga portugal",
  "jupiler",
  "belgian",
  "scottish premiership",
  "greek super",
  "austrian bundesliga",
  "swiss super",
  "saudi pro",
  "roshan",
  "j1 league",
  "j1 ",
  "j league",
  "k league 1",
  "k-league 1",
  "chinese super league",
  "copa libertadores",
  "libertadores",
  "conmebol",
  "sudamericana",
  "copa sudamericana",
  "world cup",
  "euro qualifying",
  "nations league",
  "ligue 1 tunis",
];

const TIER_C: readonly string[] = [
  "superliga",
  "veikkausliiga",
  "eliteserien",
  "allsvenskan",
  "superettan",
  "first league",
  "fortuna liga",
  "ekstraklasa",
  "liga 1",
  "liga i",
  "prva liga",
  "super liga srb",
  "superliga srb",
  "a lyga",
  "virsliga",
  "meistriliiga",
  "premier division",
  "botola",
  "egyptian premier",
  "south african premier",
  "a-league",
  "isle of man",
];

function matchesAny(hay: string, needles: readonly string[]): boolean {
  return needles.some((n) => hay.includes(n));
}

function isWomenTierD(pick: PickLeagueContext): boolean {
  const blob = foldText(`${effectiveLeagueName(pick)} ${pick.liga}`);
  if (!/(women|womens|femenin|femenino|femenina|ladies)/i.test(blob)) {
    return false;
  }
  if (matchesAny(blob, WOMEN_TIER_A_ALLOW)) {
    return false;
  }
  return true;
}

function isSerieABrazil(x: string): boolean {
  return (
    (x.includes("serie a") && (x.includes("brasil") || x.includes("brazil") || x.includes("brasileir"))) ||
    x.includes("brasileirao serie a") ||
    x.includes("brasileirão serie a")
  );
}

function isItalianSerieA(x: string): boolean {
  return x.includes("serie a") && !isSerieABrazil(x) && !x.includes("serie a women");
}

function isArgentinaTopTier(x: string): boolean {
  if (!x.includes("argentina")) {
    return false;
  }
  return (
    x.includes("liga profesional") ||
    x.includes(" lpf") ||
    x.includes("lpf ") ||
    x.includes("primera division argentina") ||
    x.endsWith(" lpf")
  );
}

function isNorthAfricaWestAsiaLigue1(x: string): boolean {
  return (
    x.includes("ligue 1") &&
    (x.includes("tunis") || x.includes("tunisia") || x.includes("alger") || x.includes("maroc") || x.includes("morocco"))
  );
}

function isTopEnglandPremier(x: string): boolean {
  if (!x.includes("premier league")) {
    return false;
  }
  if (x.includes("scottish") && x.includes("premiership")) {
    return false;
  }
  return (
    x.includes("england") ||
    x.includes("inglaterra") ||
    x.includes("reino unido") ||
    x.includes("united kingdom")
  );
}

function isTopSpainFirst(x: string): boolean {
  if (!(x.includes("spain") || x.includes("espana"))) {
    return false;
  }
  if (x.includes("segunda") || x.includes("laliga 2") || x.includes("hypermotion")) {
    return false;
  }
  return x.includes("la liga") || x.includes("laliga") || (x.includes("primera division") && !x.includes("chile") && !x.includes("argentina"));
}

function isTopGermanyBundesliga(x: string): boolean {
  if (!x.includes("bundesliga")) {
    return false;
  }
  if (x.includes("2. bundesliga") || x.includes("bundesliga 2") || x.includes("austrian")) {
    return false;
  }
  return x.includes("germany") || x.includes("alemania") || x.includes("deutsch");
}

function isTopFranceLigue1(x: string): boolean {
  if (!x.includes("ligue 1")) {
    return false;
  }
  if (isNorthAfricaWestAsiaLigue1(x)) {
    return false;
  }
  return x.includes("france") || x.includes("francia");
}

function isTopItalySerieA(x: string): boolean {
  if (!x.includes("italy") && !x.includes("italia")) {
    return false;
  }
  return isItalianSerieA(x);
}

function isTopMexicoLigaMx(x: string): boolean {
  return x.includes("liga mx") || (x.includes("mexico") && x.includes("mexican") && x.includes("liga"));
}

function isTopChilePrimera(x: string): boolean {
  return x.includes("chile") && (x.includes("primera division") || x.includes("primera chile"));
}

function isTopMls(x: string): boolean {
  return (
    x.includes("major league soccer") ||
    (x.includes("mls") && (x.includes("usa") || x.includes("united states") || x.includes("estados unidos") || x.includes("canada")))
  );
}

function isTopColombiaBetplay(x: string): boolean {
  return x.includes("colombia") && (x.includes("betplay") || x.includes("liga betplay") || x.includes("primera a"));
}

/** Nombres UEFA / FIFA que no requieren país en el string combinado. */
function isGlobalBrandTierS(nameFold: string): boolean {
  return (
    nameFold.includes("champions league") ||
    nameFold.includes("europa league") ||
    nameFold.includes("conference league") ||
    nameFold.includes("copa libertadores") ||
    nameFold.includes("libertadores") ||
    nameFold.includes("world cup") ||
    nameFold.includes("euro ") ||
    nameFold.includes("uefa nations")
  );
}

function tierFromLeagueId(id: number): LeagueTierCode | null {
  if (id <= 0) {
    return null;
  }
  if (LEAGUE_IDS_TIER_S.has(id)) {
    return "S";
  }
  if (LEAGUE_IDS_TIER_A.has(id)) {
    return "A";
  }
  if (LEAGUE_IDS_TIER_B.has(id)) {
    return "B";
  }
  return null;
}

/**
 * Tier usando id de competición, país + nombre y reglas explícitas (sin "Premier League" genérica → S).
 */
export function getLeagueTierForPick(pick: PickLeagueContext): LeagueTierCode {
  const id = pick.league_id ?? 0;
  const byId = tierFromLeagueId(id);
  if (byId) {
    return byId;
  }

  const x = combinedLeagueFold(pick);
  const nameOnly = foldText(effectiveLeagueName(pick));

  if (!x && !nameOnly) {
    return "C";
  }

  const hay = x || nameOnly;

  if (matchesAny(hay, TIER_D_SIGNALS) || isWomenTierD(pick)) {
    return "D";
  }

  if (matchesAny(hay, TIER_B)) {
    return "B";
  }

  if (
    isTopEnglandPremier(hay) ||
    isTopSpainFirst(hay) ||
    isTopGermanyBundesliga(hay) ||
    isTopFranceLigue1(hay) ||
    isTopItalySerieA(hay) ||
    isSerieABrazil(hay) ||
    isArgentinaTopTier(hay) ||
    isTopMexicoLigaMx(hay) ||
    isTopChilePrimera(hay) ||
    isTopMls(hay) ||
    isTopColombiaBetplay(hay) ||
    isGlobalBrandTierS(nameOnly) ||
    isGlobalBrandTierS(hay)
  ) {
    if (hay.includes("serie b") && !isSerieABrazil(hay)) {
      return "B";
    }
    return "S";
  }

  if (matchesAny(hay, TIER_A_STRINGS)) {
    return "A";
  }

  if ((hay.includes("turkey") || hay.includes("turkiye")) && hay.includes("super") && hay.includes("lig")) {
    return "A";
  }

  if (matchesAny(hay, TIER_C)) {
    return "C";
  }

  return "C";
}

/**
 * @deprecated Preferir `getLeagueTierForPick` con país + league_name + league_id.
 * Solo nombre/UI sin contexto: conservador (no asigna S por "Premier League" suelta).
 */
export function getLeagueTier(liga: string): LeagueTierCode {
  return getLeagueTierForPick({
    liga,
    league_id: 0,
    country: "",
    league_name: stripLeagueCountrySuffix(liga),
  });
}

/**
 * Big 5 europeas + copas UEFA (máximo prestigio editorial, no incluye LATAM).
 */
export const TOP_EU_PRESTIGE_IDS: ReadonlySet<number> = new Set([39, 140, 135, 78, 61, 2, 3, 848]);

/**
 * LATAM principal + copas (prioridad editorial Prediktia; por debajo de TOP_EU).
 * IDs API-Football v3 — revisar en dashboard si alguna competición cambia de id.
 */
export const LATAM_EDITORIAL_IDS: ReadonlySet<number> = new Set([
  265, // Chile
  128, // Argentina
  71,
  72, // Brasil A/B
  262, // México Liga MX
  239, // Colombia
  281, // Perú Liga 1
  242, // Ecuador LigaPro
  268, // Uruguay
  252, // Paraguay
  13, // Libertadores
  11, // Sudamericana
]);

export function isLatamEditorialContext(pick: PickLeagueContext): boolean {
  const id = pick.league_id ?? 0;
  if (LATAM_EDITORIAL_IDS.has(id)) {
    return true;
  }
  const x = combinedLeagueFold(pick);
  if (x.includes("libertadores") || x.includes("sudamericana")) {
    return true;
  }
  const pairs: [string, string][] = [
    ["mexico", "liga mx"],
    ["méxico", "liga mx"],
    ["chile", "primera"],
    ["argentina", "liga"],
    ["argentina", "lpf"],
    ["argentina", "primera"],
    ["brazil", "brasileir"],
    ["brasil", "brasileir"],
    ["colombia", "primera"],
    ["colombia", "betplay"],
    ["peru", "liga 1"],
    ["perú", "liga 1"],
    ["ecuador", "liga pro"],
    ["uruguay", "primera"],
    ["paraguay", "primera"],
  ];
  return pairs.some(([a, b]) => x.includes(a) && x.includes(b));
}

/** Orden visual: S primero, D último (tras estado del partido). */
export function leagueTierSortKey(tier: LeagueTierCode): number {
  return { S: 0, A: 1, B: 2, C: 3, D: 4 }[tier];
}

/** Prestige editorial (menor = más protagonismo en portada). */
function isEditorialLowTrustBlob(pick: PickLeagueContext): boolean {
  const blob = `${combinedLeagueFold(pick)} ${foldText(pick.liga)}`;
  if (
    /(women|womens|femenin|femenina|ladies)\b/i.test(blob) &&
    !matchesAny(blob, WOMEN_TIER_A_ALLOW)
  ) {
    return true;
  }
  if (
    matchesAny(blob, [
      "regional",
      "amateur",
      "reserva",
      "reserve",
      "juvenil",
      "youth",
      "u19",
      "u20",
      "u21",
      "u22",
      "tercera division",
      "liga iii",
      "segunda b",
      "district",
    ])
  ) {
    return true;
  }
  return false;
}

export function leaguePrestigeSortKey(pick: PickLeagueContext): number {
  const id = pick.league_id ?? 0;
  if (TOP_EU_PRESTIGE_IDS.has(id)) {
    return 0;
  }
  if (LATAM_EDITORIAL_IDS.has(id) || isLatamEditorialContext(pick)) {
    return 1;
  }
  if (LEAGUE_IDS_TIER_S.has(id)) {
    return 2;
  }
  if (LEAGUE_IDS_TIER_A.has(id)) {
    return 3;
  }
  if (LEAGUE_IDS_TIER_B.has(id)) {
    return 4;
  }
  const lt = getLeagueTierForPick(pick);
  if (lt === "D") {
    return 14;
  }
  if (isEditorialLowTrustBlob(pick)) {
    return 11;
  }
  if (lt === "S") {
    return 2;
  }
  if (lt === "A") {
    return 5;
  }
  if (lt === "B") {
    return 6;
  }
  return 9;
}

/** Refuerzo de ranking: Europa top > LATAM principal > otras S/A… */
export function rankScoreHeadlineBoost(pick: PickLeagueContext): number {
  const id = pick.league_id ?? 0;
  if (TOP_EU_PRESTIGE_IDS.has(id)) {
    return 118;
  }
  if (LATAM_EDITORIAL_IDS.has(id) || isLatamEditorialContext(pick)) {
    return 82;
  }
  if (LEAGUE_IDS_TIER_S.has(id)) {
    return 68;
  }
  if (LEAGUE_IDS_TIER_A.has(id)) {
    return 48;
  }
  const lt = getLeagueTierForPick(pick);
  if (lt === "S") {
    return 62;
  }
  if (lt === "A") {
    return 36;
  }
  if (lt === "B") {
    return 16;
  }
  return 0;
}

/** Penalización fuerte a EV “gritón” en contextos de baja confianza. */
export function rankScoreBuryPenalty(pick: PickLeagueContext, ev: number): number {
  const lt = getLeagueTierForPick(pick);
  const blob = foldText([effectiveCountry(pick), effectiveLeagueName(pick), pick.liga].filter(Boolean).join(" "));
  let pen = 0;
  if (lt === "D") {
    pen += 125 + ev * 280;
  } else if (lt === "C") {
    pen += 48 + ev * 115;
  }
  if (
    /(women|womens|femenin|femenina|ladies)\b/i.test(blob) &&
    !matchesAny(blob, WOMEN_TIER_A_ALLOW)
  ) {
    pen += 62 + ev * 145;
  }
  if (
    matchesAny(blob, [
      "regional",
      "amateur",
      "reserva",
      "reserve",
      "juvenil",
      "youth",
      "u19",
      "u20",
      "u21",
      "tercera",
      "liga iii",
    ])
  ) {
    pen += 52 + ev * 105;
  }
  return pen;
}

/** Ajuste al confidenceScore por tier (filtro duro complementa esto). */
export function leagueTierScoreDelta(tier: LeagueTierCode): number {
  switch (tier) {
    case "S":
      return 42;
    case "A":
      return 30;
    case "B":
      return 10;
    case "C":
      return -6;
    case "D":
      return -52;
    default:
      return 0;
  }
}
