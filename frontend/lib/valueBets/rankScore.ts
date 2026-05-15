import { isDrawPick } from "./classifyValuePick";
import { computeConfidenceScore } from "./confidenceScore";
import {
  foldText,
  getLeagueTierForPick,
  rankScoreBuryPenalty,
  rankScoreHeadlineBoost,
  type LeagueTierCode,
} from "./leagueTiers";
import type { ValueBetPick } from "./types";

function impliedOdds(cuota: number): number {
  return 1 / cuota;
}

/** Proxy de “volumen histórico / liquidez de competición” por tier. */
function historicalVolumeProxy(lt: LeagueTierCode): number {
  return { S: 24, A: 19, B: 11, C: 4, D: 0 }[lt];
}

/** Liquidez implícita + estabilidad de cuota (mainlines estrechos vs extremos). */
function liquidityAndOddsStability(cuota: number): number {
  let s = 12;
  if (cuota >= 1.48 && cuota <= 2.35) {
    s += 18;
  } else if (cuota <= 2.75) {
    s += 10;
  } else if (cuota <= 3.15) {
    s += 0;
  } else {
    s -= 14;
  }
  if (cuota > 4.0) {
    s -= 28;
  }
  if (cuota > 5.0) {
    s -= 16;
  }
  return s;
}

/** Mercados más “mainline” y predecibles suben el ranking. */
function marketSolidityScore(mercado: string, pickLabel: string): number {
  const pk = foldText(pickLabel);
  if (mercado === "1X2" && (pk === "victoria local" || pk === "victoria visitante")) {
    return 28;
  }
  if (mercado === "Doble oportunidad") {
    return 23;
  }
  if (mercado === "Total goles") {
    return 16;
  }
  if (mercado === "Ambos marcan") {
    return 12;
  }
  if (mercado === "1X2" && pk === "empate") {
    return 5;
  }
  return 10;
}

function probRealisticScore(p: number): number {
  if (p >= 0.52 && p <= 0.66) {
    return 22;
  }
  if (p >= 0.46 && p < 0.52) {
    return 14;
  }
  if (p > 0.66 && p <= 0.74) {
    return 9;
  }
  if (p < 0.42) {
    return -10;
  }
  return 7;
}

function volatileAndStructuralPenalty(pick: ValueBetPick): number {
  let pen = 0;
  if (isDrawPick(pick)) {
    pen += 38;
  }
  if (pick.mercado === "Ambos marcan" && pick.cuota > 2.55) {
    pen += 14;
  }
  if (pick.mercado === "Total goles" && pick.cuota > 2.9) {
    pen += 12;
  }
  if (pick.mercado === "Ambos marcan" && pick.cuota > 3.1) {
    pen += 10;
  }
  return pen;
}

/** EV influye menos en ligas débiles (evita dominar el TOP con exóticos). */
function evTierShrink(lt: LeagueTierCode): number {
  return { S: 1, A: 0.82, B: 0.38, C: 0.12, D: 0.028 }[lt];
}

/**
 * Score editorial para ordenar la lista: combina confidence, tier, liquidez de cuota,
 * solidez de mercado, probabilidad realista y EV ponderado (no orden EV puro).
 */
export function computeRankScore(pick: ValueBetPick): number {
  const lt = getLeagueTierForPick(pick);
  const conf = computeConfidenceScore(pick);
  const O = pick.cuota;
  const p = pick.probabilidad;
  const edge = p - impliedOdds(O);

  const vol = historicalVolumeProxy(lt);
  const liq = liquidityAndOddsStability(O);
  const mkt = marketSolidityScore(pick.mercado, pick.pick);
  const probR = probRealisticScore(p);
  const edgeScore = Math.min(30, Math.max(-8, edge * 100));
  const evPart = pick.ev * 52 * evTierShrink(lt);
  const pen = volatileAndStructuralPenalty(pick);
  const bury = rankScoreBuryPenalty(pick, pick.ev);
  const head = rankScoreHeadlineBoost(pick);

  return (
    conf * 2.45 +
    vol * 3.55 +
    liq * 2.2 +
    mkt * 2.55 +
    probR * 1.95 +
    edgeScore +
    evPart -
    pen -
    bury +
    head
  );
}
