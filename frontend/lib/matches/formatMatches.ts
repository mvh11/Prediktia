import { FormatMatchesError } from "./errors";
import type {
  ApiFootballFixtureItem,
  FormattedMatch,
  FormatMatchesOptions,
} from "./types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readString(value: unknown): string | undefined {
  if (typeof value === "string" && value.trim().length > 0) {
    return value.trim();
  }
  return undefined;
}

function readNumberOrNull(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return null;
}

function buildEstadoPartido(fixture: ApiFootballFixtureItem["fixture"]): string {
  const long = fixture?.status?.long?.trim();
  const short = fixture?.status?.short?.trim();
  const elapsed = fixture?.status?.elapsed;

  if (long && short && long !== short) {
    return `${short} — ${long}`;
  }
  if (long) {
    return long;
  }
  if (short) {
    return short;
  }
  if (typeof elapsed === "number" && Number.isFinite(elapsed)) {
    return `En juego (${elapsed}′)`;
  }
  return "Desconocido";
}

function mapSingle(item: unknown, index: number): FormattedMatch {
  if (!isRecord(item)) {
    throw new FormatMatchesError(
      "INVALID_FIXTURE_SHAPE",
      `El elemento en el índice ${index} no es un objeto.`,
      { cause: { index, item } }
    );
  }

  const row = item as ApiFootballFixtureItem;
  const fixture = row.fixture;
  const fixtureId = fixture?.id;
  const fecha = readString(fixture?.date);
  const liga = readString(row.league?.name) ?? "—";
  const pais = readString(row.league?.country) ?? "—";
  const equipoLocal = readString(row.teams?.home?.name) ?? "—";
  const equipoVisitante = readString(row.teams?.away?.name) ?? "—";
  const golesLocal = readNumberOrNull(row.goals?.home);
  const golesVisitante = readNumberOrNull(row.goals?.away);

  if (typeof fixtureId !== "number" || !Number.isFinite(fixtureId)) {
    throw new FormatMatchesError(
      "INVALID_FIXTURE_SHAPE",
      `Falta fixture.id válido en el índice ${index}.`,
      { cause: { index, item } }
    );
  }

  if (!fecha) {
    throw new FormatMatchesError(
      "INVALID_FIXTURE_SHAPE",
      `Falta fixture.date en el índice ${index}.`,
      { cause: { index, item } }
    );
  }

  return {
    fixture_id: fixtureId,
    fecha,
    liga,
    pais,
    equipo_local: equipoLocal,
    equipo_visitante: equipoVisitante,
    goles_local: golesLocal,
    goles_visitante: golesVisitante,
    estado_partido: buildEstadoPartido(fixture),
  };
}

/**
 * Normaliza `raw_fixtures` (array tal como lo devuelve tu backend desde API-Football)
 * a un listado homogéneo para la UI o análisis posterior.
 *
 * @throws {FormatMatchesError} Si `rawFixtures` no es un array, o en modo `strict` si algún item es inválido.
 */
export function formatMatches(
  rawFixtures: unknown,
  options?: FormatMatchesOptions
): FormattedMatch[] {
  if (!Array.isArray(rawFixtures)) {
    throw new FormatMatchesError(
      "INVALID_INPUT",
      "raw_fixtures debe ser un array.",
      { cause: { received: typeof rawFixtures } }
    );
  }

  const strict = options?.strict === true;
  const out: FormattedMatch[] = [];

  for (let i = 0; i < rawFixtures.length; i++) {
    try {
      out.push(mapSingle(rawFixtures[i], i));
    } catch (err) {
      if (strict) {
        if (err instanceof FormatMatchesError) {
          throw err;
        }
        throw new FormatMatchesError(
          "INVALID_FIXTURE_SHAPE",
          `Error al parsear el índice ${i}.`,
          { cause: err }
        );
      }

      const reason =
        err instanceof Error ? err.message : "Error desconocido al mapear la fila.";
      options?.onSkip?.({ index: i, reason });
    }
  }

  return out;
}
