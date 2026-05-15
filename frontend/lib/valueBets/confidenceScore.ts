import type { ValueBetPick } from "./types";

import { foldText, getLeagueTierForPick, leagueTierScoreDelta } from "./leagueTiers";

function impliedFromOdds(cuota: number): number {
  return 1 / cuota;
}

function marketStabilityBonus(mercado: string, pickLabel: string): number {
  const pk = foldText(pickLabel);
  let b = 0;
  if (mercado === "Total goles") {
    b += 6;
  }
  if (mercado === "Ambos marcan") {
    b += 5;
  }
  if (mercado === "Doble oportunidad") {
    b += 4;
  }
  if (mercado === "1X2" && pk !== "empate") {
    b += 2;
  }
  if (mercado === "1X2" && (pk === "victoria local" || pk === "victoria visitante")) {
    b += 2;
  }
  return b;
}

function marketInstabilityPenalty(mercado: string, pickLabel: string, cuota: number): number {
  const pk = foldText(pickLabel);
  let pen = 0;
  if (mercado === "1X2" && pk === "empate") {
    pen -= 30;
  }
  if (mercado === "Ambos marcan" && cuota > 2.55) {
    pen -= 8;
  }
  if (mercado === "Total goles" && cuota > 2.65) {
    pen -= 6;
  }
  if (mercado === "1X2" && pk === "empate" && cuota > 2.35) {
    pen -= 10;
  }
  return pen;
}

function probabilityBlock(p: number): number {
  if (p >= 0.64) {
    return 14;
  }
  if (p >= 0.58) {
    return 9;
  }
  if (p >= 0.52) {
    return 4;
  }
  if (p >= 0.48) {
    return -2;
  }
  if (p >= 0.42) {
    return -12;
  }
  return -22;
}

function oddsBlock(cuota: number): number {
  if (cuota <= 1.75) {
    return 8;
  }
  if (cuota <= 2.05) {
    return 6;
  }
  if (cuota <= 2.45) {
    return 3;
  }
  if (cuota <= 2.85) {
    return -4;
  }
  if (cuota <= 3.2) {
    return -12;
  }
  return -24;
}

/**
 * Puntuación 0–100 de confianza / calidad percibida del pick (heurística client-side).
 * Combina liga, mercado, cuota, probabilidad, edge vs implícita y estabilidad.
 */
export function computeConfidenceScore(pick: ValueBetPick): number {
  const tier = getLeagueTierForPick(pick);
  let s =
    46 +
    leagueTierScoreDelta(tier) +
    marketStabilityBonus(pick.mercado, pick.pick) +
    marketInstabilityPenalty(pick.mercado, pick.pick, pick.cuota) +
    probabilityBlock(pick.probabilidad) +
    oddsBlock(pick.cuota);

  const implied = impliedFromOdds(pick.cuota);
  const edge = pick.probabilidad - implied;
  if (edge >= 0.06) {
    s += 7;
  } else if (edge >= 0.035) {
    s += 4;
  } else if (edge < 0.012) {
    s -= 6;
  }

  if (pick.ev >= 0.11 && pick.probabilidad >= 0.54 && pick.cuota <= 2.5) {
    s += 3;
  }

  return Math.max(0, Math.min(100, Math.round(s)));
}
