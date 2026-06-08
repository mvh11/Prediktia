import { foldText } from "@/lib/valueBets/leagueTiers";

export type LeagueCatalogEntry = {
  key: string;
  label: string;
  fixtureCount: number;
};

/** Etiqueta legible: "Primera División (Chile)". */
export function formatLeagueLabel(name: string, country: string): string {
  const league = name.trim();
  const nation = country.trim();
  if (!league) {
    return nation || "—";
  }
  if (!nation || league.includes(`(${nation})`)) {
    return league;
  }
  return `${league} (${nation})`;
}

export function leagueKeyFromParts(country: string, leagueName: string, leagueId?: number): string {
  if (leagueId != null && leagueId > 0) {
    return `id:${leagueId}`;
  }
  return `txt:${foldText(country)}|${foldText(leagueName)}`;
}

export function buildLeagueCatalog(
  rows: Array<{ key: string; label: string; fixtureId: number }>,
): LeagueCatalogEntry[] {
  const map = new Map<string, { label: string; fixtures: Set<number> }>();
  for (const row of rows) {
    let entry = map.get(row.key);
    if (!entry) {
      entry = { label: row.label, fixtures: new Set() };
      map.set(row.key, entry);
    }
    entry.fixtures.add(row.fixtureId);
  }
  return [...map.entries()]
    .map(([key, value]) => ({
      key,
      label: value.label,
      fixtureCount: value.fixtures.size,
    }))
    .sort((a, b) => b.fixtureCount - a.fixtureCount || a.label.localeCompare(b.label, "es"));
}
