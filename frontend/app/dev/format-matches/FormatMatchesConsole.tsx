"use client";

import { useEffect, useState } from "react";

import {
  formatMatches,
  FormatMatchesError,
  type FormattedMatch,
} from "@/lib/matches";

const DEFAULT_BACKEND = "http://127.0.0.1:8000";

const MATCHES_BASE =
  (typeof process !== "undefined" &&
    process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "")) ||
  DEFAULT_BACKEND;

type MatchesApiPayload = {
  raw_fixtures?: unknown;
};

let devMatchesCache: FormattedMatch[] | null = null;
let devMatchesInflight: Promise<FormattedMatch[]> | null = null;

/**
 * Una sola petición al upstream por proceso: reutiliza caché o la promesa en curso
 * (útil con Strict Mode / remontajes sin bucles de fetch).
 */
function fetchFormattedMatchesOnce(): Promise<FormattedMatch[]> {
  if (devMatchesCache) {
    return Promise.resolve(devMatchesCache);
  }
  if (devMatchesInflight) {
    return devMatchesInflight;
  }

  devMatchesInflight = (async () => {
    const res = await fetch(`${MATCHES_BASE}/matches`, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status} al llamar ${MATCHES_BASE}/matches`);
    }
    const data = (await res.json()) as MatchesApiPayload;
    const clean = formatMatches(data.raw_fixtures);
    devMatchesCache = clean;
    return clean;
  })();

  return devMatchesInflight.finally(() => {
    devMatchesInflight = null;
  });
}

function scoreLabel(value: number | null): string {
  return value === null || value === undefined ? "—" : String(value);
}

export function FormatMatchesConsole() {
  const [matches, setMatches] = useState<FormattedMatch[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchFormattedMatchesOnce()
      .then((clean) => {
        if (cancelled) {
          return;
        }
        setMatches(clean);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) {
          return;
        }
        if (err instanceof FormatMatchesError) {
          setError(`${err.code}: ${err.message}`);
          return;
        }
        setError(err instanceof Error ? err.message : "Error desconocido");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-6 text-gray-200">
      <header className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <h1 className="text-lg font-semibold text-white">Dev · formatMatches</h1>
        <p className="mt-2 text-sm text-gray-400">
          Partidos formateados desde{" "}
          <code className="rounded bg-gray-800 px-1.5 py-0.5 text-xs text-cyan-300">
            {MATCHES_BASE}/matches
          </code>
          . Opcional:{" "}
          <code className="rounded bg-gray-800 px-1 py-0.5 text-xs">
            NEXT_PUBLIC_BACKEND_URL
          </code>{" "}
          en <code className="rounded bg-gray-800 px-1 py-0.5 text-xs">.env.local</code>.
        </p>
      </header>

      {loading && (
        <p className="rounded-lg border border-gray-800 bg-gray-900/80 px-4 py-3 text-sm text-gray-400">
          Cargando partidos…
        </p>
      )}

      {error && !loading && (
        <p
          className="rounded-lg border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200"
          role="alert"
        >
          {error}
        </p>
      )}

      {!loading && !error && matches && matches.length === 0 && (
        <p className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-3 text-sm text-gray-400">
          No hay partidos para la fecha consultada.
        </p>
      )}

      {!loading && !error && matches && matches.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-gray-800 bg-gray-900 shadow-lg shadow-black/20">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-800 text-left text-sm">
              <thead className="bg-gray-950/80 text-xs font-semibold uppercase tracking-wide text-gray-400">
                <tr>
                  <th className="whitespace-nowrap px-4 py-3">Local</th>
                  <th className="whitespace-nowrap px-4 py-3">Visitante</th>
                  <th className="whitespace-nowrap px-3 py-3 text-center">Goles L</th>
                  <th className="whitespace-nowrap px-3 py-3 text-center">Goles V</th>
                  <th className="whitespace-nowrap px-4 py-3">Liga</th>
                  <th className="whitespace-nowrap px-4 py-3">Fecha</th>
                  <th className="whitespace-nowrap px-4 py-3">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {matches.map((m) => (
                  <tr
                    key={m.fixture_id}
                    className="transition-colors hover:bg-gray-800/50"
                  >
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-white">
                      {m.equipo_local}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-white">
                      {m.equipo_visitante}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-center tabular-nums text-gray-300">
                      {scoreLabel(m.goles_local)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-center tabular-nums text-gray-300">
                      {scoreLabel(m.goles_visitante)}
                    </td>
                    <td className="max-w-[200px] truncate px-4 py-3 text-gray-400" title={m.liga}>
                      {m.liga}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-400 tabular-nums">
                      {m.fecha}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-cyan-300/90">
                      {m.estado_partido}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
