import type { ValueBetPick } from "./types";

import { foldText } from "./leagueTiers";

function shortClubName(name: string, max = 16): string {
  const t = name.trim();
  if (t.length <= max) {
    return t;
  }
  return `${t.slice(0, max - 1)}…`;
}

/**
 * Texto compacto para pill del pick principal (card portada).
 */
export function formatHeroPickPill(pick: ValueBetPick): string {
  const home = pick.equipo_local.trim() || "Local";
  const away = pick.equipo_visitante.trim() || "Visita";
  const pk = foldText(pick.pick);

  if (pick.mercado === "Doble oportunidad") {
    const raw = pick.pick.trim().toUpperCase();
    if (raw === "1X") {
      return `1X · ${shortClubName(home)} o empate`;
    }
    if (raw === "X2") {
      return `X2 · empate o ${shortClubName(away)}`;
    }
    if (raw === "12") {
      return `12 · ${shortClubName(home)} o ${shortClubName(away)}`;
    }
    return `${raw} · doble`;
  }

  if (pick.mercado === "1X2") {
    if (pk === "victoria local") {
      return `1 · ${shortClubName(home)}`;
    }
    if (pk === "empate") {
      return "X · Empate";
    }
    if (pk === "victoria visitante") {
      return `2 · ${shortClubName(away)}`;
    }
  }

  if (pick.mercado === "Total goles") {
    return pick.pick;
  }

  if (pick.mercado === "Ambos marcan") {
    return pick.pick === "Sí" || foldText(pick.pick) === "si" ? "BTTS · Sí" : "BTTS · No";
  }

  return `${pick.mercado}: ${pick.pick}`;
}

/**
 * Texto de resultado alineado con convención casa / visitante / empate
 * (referencial; las cuotas siguen siendo las del backend).
 */
export function formatPickOutcomeLabel(pick: ValueBetPick): string {
  const home = pick.equipo_local.trim() || "Local";
  const away = pick.equipo_visitante.trim() || "Visitante";
  const pk = foldText(pick.pick);

  if (pick.mercado === "1X2") {
    if (pk === "victoria local") {
      return `Victoria local (${home})`;
    }
    if (pk === "victoria visitante") {
      return `Victoria visitante (${away})`;
    }
    if (pk === "empate") {
      return "Empate";
    }
  }

  if (pick.mercado === "Doble oportunidad") {
    const raw = pick.pick.trim().toUpperCase();
    if (raw === "1X") {
      return `1X · ${home} o empate`;
    }
    if (raw === "X2") {
      return `X2 · empate o ${away}`;
    }
    if (raw === "12") {
      return `12 · ${home} o ${away} (sin empate)`;
    }
    return `${pick.pick} (doble oportunidad)`;
  }

  if (pick.mercado === "Total goles") {
    return pick.pick;
  }

  if (pick.mercado === "Ambos marcan") {
    return pick.pick === "Sí" || foldText(pick.pick) === "si" ? "Ambos marcan: sí" : "Ambos marcan: no";
  }

  return pick.pick;
}

/** Una línea corta para la portada: categoría + resultado. */
export function formatPickSummaryLine(pick: ValueBetPick): string {
  return `${pick.mercado}: ${formatPickOutcomeLabel(pick)}`;
}
