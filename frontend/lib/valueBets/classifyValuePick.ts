import { computeConfidenceScore } from "./confidenceScore";
import { type ValueGrade } from "./evPresentation";
import { foldText, getLeagueTierForPick, type LeagueTierCode } from "./leagueTiers";
import type { ValueBetPick } from "./types";

function impliedFromOdds(cuota: number): number {
  return 1 / cuota;
}

export function isDrawPick(pick: ValueBetPick): boolean {
  return foldText(pick.pick) === "empate";
}

/** Solo 1X2 (no empate) o Doble oportunidad pueden aspirar a ELITE. */
function canMarketBeElite(pick: ValueBetPick): boolean {
  if (pick.mercado === "Doble oportunidad") {
    return true;
  }
  if (pick.mercado !== "1X2") {
    return false;
  }
  const pk = foldText(pick.pick);
  return pk === "victoria local" || pk === "victoria visitante";
}

/** ELITE solo Tier S / A + reglas de mercado y cuotas. */
function neverEliteHard(pick: ValueBetPick, lt: LeagueTierCode): boolean {
  if (lt !== "S" && lt !== "A") {
    return true;
  }
  if (isDrawPick(pick)) {
    return true;
  }
  if (!canMarketBeElite(pick)) {
    return true;
  }
  if (pick.probabilidad < 0.57) {
    return true;
  }
  if (pick.cuota > 2.58 || pick.cuota < 1.5) {
    return true;
  }
  return false;
}

function isHardRisky(pick: ValueBetPick, score: number, lt: LeagueTierCode): boolean {
  if (pick.probabilidad < 0.405) {
    return true;
  }
  if (pick.cuota > 3.35) {
    return true;
  }
  if (pick.cuota > 3.2 && pick.probabilidad < 0.46) {
    return true;
  }
  if (lt === "D" && score < 48) {
    return true;
  }
  return false;
}

function applyLeagueTierCap(grade: ValueGrade, lt: LeagueTierCode, score: number, ev: number, prob: number): ValueGrade {
  if (lt === "D") {
    if (grade === "elite" || grade === "high") {
      return "good";
    }
    return grade;
  }
  if (lt === "C") {
    if (grade === "elite" || grade === "high") {
      return "good";
    }
    return grade;
  }
  if (lt === "B") {
    if (grade === "elite") {
      return "high";
    }
    if (grade === "high" && (score < 79 || ev < 0.072 || prob < 0.52)) {
      return "good";
    }
  }
  return grade;
}

/**
 * Clasificación por tier de liga (S/A/B/C/D) + confidenceScore + EV.
 * ELITE: solo S/A. HIGH: S/A, o B con umbral más estricto. C/D sin HIGH/ELITE.
 */
export function classifyValuePick(pick: ValueBetPick): ValueGrade {
  const lt = getLeagueTierForPick(pick);
  const score = computeConfidenceScore(pick);

  if (isDrawPick(pick)) {
    return "risky";
  }

  if (pick.cuota > 3.2 || pick.probabilidad < 0.45) {
    return "risky";
  }

  if (isHardRisky(pick, score, lt)) {
    return "risky";
  }

  if (score < 38) {
    return "risky";
  }

  const implied = impliedFromOdds(pick.cuota);
  const edge = pick.probabilidad - implied;

  const eliteFloor = lt === "S" ? 86 : 90;

  let grade: ValueGrade = "good";

  if (
    !neverEliteHard(pick, lt) &&
    (lt === "S" || lt === "A") &&
    score >= eliteFloor &&
    pick.ev >= 0.092 &&
    pick.probabilidad >= 0.6 &&
    pick.cuota >= 1.52 &&
    pick.cuota <= 2.36 &&
    edge >= 0.03
  ) {
    grade = "elite";
  } else if (
    (lt === "S" || lt === "A") &&
    score >= 74 &&
    pick.ev >= 0.066 &&
    pick.probabilidad >= 0.48 &&
    pick.cuota <= 3.05
  ) {
    grade = "high";
  } else if (
    lt === "B" &&
    score >= 79 &&
    pick.ev >= 0.072 &&
    pick.probabilidad >= 0.52 &&
    pick.cuota <= 3.05
  ) {
    grade = "high";
  } else if (score >= 45) {
    grade = "good";
  } else {
    grade = "risky";
  }

  return applyLeagueTierCap(grade, lt, score, pick.ev, pick.probabilidad);
}
