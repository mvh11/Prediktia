"use client";

import { useEffect, useMemo, useState } from "react";

import {
  fetchFormattedMatchesOnce,
  FormatMatchesError,
  partitionMatchesByBucket,
  type FormattedMatch,
} from "@/lib/matches";

type MatchTab = "all" | "live" | "upcoming" | "finished";

function scoreLabel(value: number | null): string {
  return value === null || value === undefined ? "—" : String(value);
}

function formatKickoff(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat("es", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

function MatchCard({ m }: { m: FormattedMatch }) {
  return (
    <article className="group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-zinc-900/90 via-zinc-950 to-black p-5 shadow-xl shadow-black/40 transition hover:border-emerald-500/30 hover:shadow-emerald-900/20">
      <div className="mb-4 flex items-start justify-between gap-2">
        <p
          className="line-clamp-2 min-w-0 text-xs font-medium uppercase tracking-wide text-zinc-500"
          title={m.liga}
        >
          {m.liga}
        </p>
        <time
          className="shrink-0 rounded-lg bg-white/5 px-2 py-1 text-xs tabular-nums text-emerald-400/90"
          dateTime={m.fecha}
        >
          {formatKickoff(m.fecha)}
        </time>
      </div>

      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-white" title={m.equipo_local}>
            {m.equipo_local}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2 rounded-xl bg-black/50 px-3 py-2 ring-1 ring-white/10">
          <span className="text-2xl font-black tabular-nums text-white">
            {scoreLabel(m.goles_local)}
          </span>
          <span className="text-lg font-bold text-zinc-600">:</span>
          <span className="text-2xl font-black tabular-nums text-white">
            {scoreLabel(m.goles_visitante)}
          </span>
        </div>
        <div className="min-w-0 flex-1 text-right">
          <p
            className="truncate text-sm font-semibold text-white"
            title={m.equipo_visitante}
          >
            {m.equipo_visitante}
          </p>
        </div>
      </div>

      <div className="mt-4 flex justify-center">
        <span className="inline-flex max-w-full items-center rounded-full bg-zinc-800/80 px-3 py-1 text-center text-xs font-medium text-cyan-300/95 ring-1 ring-cyan-500/20">
          <span className="truncate" title={m.estado_partido}>
            {m.estado_partido}
          </span>
        </span>
      </div>
    </article>
  );
}

function Section({
  title,
  subtitle,
  accent,
  matches,
  emptyLabel,
}: {
  title: string;
  subtitle: string;
  accent: "emerald" | "sky" | "zinc";
  matches: FormattedMatch[];
  emptyLabel: string;
}) {
  const accentRing =
    accent === "emerald"
      ? "ring-emerald-500/40"
      : accent === "sky"
        ? "ring-sky-500/40"
        : "ring-zinc-600/50";
  const dot =
    accent === "emerald"
      ? "bg-emerald-400 shadow-emerald-400/60 animate-pulse"
      : accent === "sky"
        ? "bg-sky-400 shadow-sky-400/50"
        : "bg-zinc-500";

  return (
    <section className={`rounded-2xl ring-1 ${accentRing} bg-zinc-950/40 p-5 sm:p-6`}>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-bold tracking-tight text-white">
            <span className={`h-2.5 w-2.5 rounded-full shadow-lg ${dot}`} aria-hidden />
            {title}
          </h2>
          <p className="mt-1 text-sm text-zinc-500">{subtitle}</p>
        </div>
        <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-semibold tabular-nums text-zinc-400 ring-1 ring-white/10">
          {matches.length}
        </span>
      </div>

      {matches.length === 0 ? (
        <p className="rounded-xl border border-dashed border-zinc-800 bg-zinc-900/30 py-10 text-center text-sm text-zinc-500">
          {emptyLabel}
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {matches.map((m) => (
            <MatchCard key={m.fixture_id} m={m} />
          ))}
        </div>
      )}
    </section>
  );
}

const TAB_ITEMS: { id: MatchTab; label: string }[] = [
  { id: "all", label: "Todos" },
  { id: "live", label: "En vivo" },
  { id: "upcoming", label: "Próximos" },
  { id: "finished", label: "Finalizados" },
];

function matchesSearchFilter(list: FormattedMatch[], query: string): FormattedMatch[] {
  const q = query.trim().toLowerCase();
  if (!q) {
    return list;
  }
  return list.filter((m) => {
    const liga = m.liga.toLowerCase();
    const local = m.equipo_local.toLowerCase();
    const visit = m.equipo_visitante.toLowerCase();
    return liga.includes(q) || local.includes(q) || visit.includes(q);
  });
}

export function MatchesBoard() {
  const [matches, setMatches] = useState<FormattedMatch[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<MatchTab>("all");
  const [searchQuery, setSearchQuery] = useState("");

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

  const hasSearch = searchQuery.trim().length > 0;

  const filteredMatches = useMemo(() => {
    if (!matches) {
      return null;
    }
    return matchesSearchFilter(matches, searchQuery);
  }, [matches, searchQuery]);

  const { live, upcoming, finished } = useMemo(() => {
    if (!filteredMatches) {
      return { live: [] as FormattedMatch[], upcoming: [] as FormattedMatch[], finished: [] as FormattedMatch[] };
    }
    return partitionMatchesByBucket(filteredMatches);
  }, [filteredMatches]);

  const tabCounts = useMemo(() => {
    if (!filteredMatches) {
      return { all: 0, live: 0, upcoming: 0, finished: 0 };
    }
    const p = partitionMatchesByBucket(filteredMatches);
    return {
      all: filteredMatches.length,
      live: p.live.length,
      upcoming: p.upcoming.length,
      finished: p.finished.length,
    };
  }, [filteredMatches]);

  const showToolbar = !loading && !error && matches && matches.length > 0;
  const noSearchResults =
    Boolean(filteredMatches && matches && matches.length > 0 && filteredMatches.length === 0 && hasSearch);

  const emptySearchHint =
    "Ningún partido coincide con tu búsqueda. Prueba con otro equipo, liga o limpia el filtro.";

  return (
    <div className="min-h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-emerald-950/40 via-zinc-950 to-black pb-16 pt-8">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <header className="mb-10 text-center sm:text-left">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-400/80">
            Prediktia
          </p>
          <h1 className="mt-2 bg-gradient-to-r from-white via-zinc-100 to-zinc-400 bg-clip-text text-3xl font-black tracking-tight text-transparent sm:text-4xl">
            Partidos del día
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-sm text-zinc-500 sm:mx-0">
            Datos en vivo desde tu backend. Si ya visitaste otra vista con la misma
            sesión, se reutiliza la caché sin nuevas peticiones.
          </p>
        </header>

        {loading && (
          <div className="flex justify-center py-20">
            <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-zinc-900/80 px-6 py-4 text-sm text-zinc-400 shadow-xl">
              <span
                className="h-5 w-5 animate-spin rounded-full border-2 border-emerald-500/30 border-t-emerald-400"
                aria-hidden
              />
              Cargando calendario…
            </div>
          </div>
        )}

        {error && !loading && (
          <p
            className="mx-auto max-w-lg rounded-2xl border border-red-500/30 bg-red-950/50 px-5 py-4 text-center text-sm text-red-200"
            role="alert"
          >
            {error}
          </p>
        )}

        {!loading && !error && matches && matches.length === 0 && (
          <p className="rounded-2xl border border-zinc-800 bg-zinc-900/50 py-16 text-center text-zinc-500">
            No hay partidos para mostrar en esta fecha.
          </p>
        )}

        {showToolbar && (
          <div className="mb-8 space-y-4">
            <div className="-mx-1 overflow-x-auto pb-1 sm:mx-0">
              <div
                className="flex min-w-0 gap-2 px-1 sm:flex-wrap sm:px-0"
                role="tablist"
                aria-label="Filtrar partidos"
              >
                {TAB_ITEMS.map(({ id, label }) => {
                  const selected = tab === id;
                  const count = tabCounts[id];
                  return (
                    <button
                      key={id}
                      type="button"
                      role="tab"
                      aria-selected={selected}
                      onClick={() => setTab(id)}
                      className={[
                        "shrink-0 rounded-xl border px-3.5 py-2.5 text-sm font-semibold transition sm:px-4",
                        selected
                          ? "border-emerald-500/45 bg-emerald-500/15 text-emerald-100 shadow-[0_0_20px_-8px_rgba(16,185,129,0.55)]"
                          : "border-white/10 bg-zinc-900/60 text-zinc-400 hover:border-white/20 hover:bg-zinc-800/80 hover:text-zinc-200",
                      ].join(" ")}
                    >
                      <span>{label}</span>
                      <span
                        className={[
                          "ml-2 inline-flex min-w-[1.5rem] justify-center rounded-md px-1.5 py-0.5 text-xs tabular-nums ring-1",
                          selected
                            ? "bg-black/30 text-emerald-200/90 ring-emerald-500/25"
                            : "bg-black/20 text-zinc-500 ring-white/10",
                        ].join(" ")}
                      >
                        {count}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <label className="block">
              <span className="sr-only">Buscar por equipo o liga</span>
              <div className="relative">
                <span
                  className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500"
                  aria-hidden
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M21 21l-4.35-4.35M10 18a8 8 0 100-16 8 8 0 000 16z"
                    />
                  </svg>
                </span>
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Buscar por equipo o liga…"
                  autoComplete="off"
                  className={`w-full rounded-xl border border-white/10 bg-zinc-900/70 py-3 pl-10 text-sm text-white shadow-inner shadow-black/30 outline-none ring-0 placeholder:text-zinc-600 focus:border-emerald-500/40 focus:bg-zinc-900 focus:ring-2 focus:ring-emerald-500/25 ${hasSearch ? "pr-20" : "pr-4"}`}
                />
                {hasSearch ? (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-xs font-medium text-zinc-500 transition hover:bg-white/10 hover:text-zinc-200"
                  >
                    Limpiar
                  </button>
                ) : null}
              </div>
            </label>
          </div>
        )}

        {noSearchResults && (
          <p className="mb-8 rounded-2xl border border-dashed border-zinc-700 bg-zinc-900/40 px-5 py-8 text-center text-sm text-zinc-400">
            {emptySearchHint}
          </p>
        )}

        {!loading && !error && matches && matches.length > 0 && !noSearchResults && (
          <div className="space-y-12">
            {(tab === "all" || tab === "live") && (
              <Section
                title="En vivo"
                subtitle="Partidos en curso o interrumpidos"
                accent="emerald"
                matches={live}
                emptyLabel={
                  hasSearch
                    ? "Ningún partido en directo coincide con tu búsqueda."
                    : "Ningún partido en directo ahora mismo."
                }
              />
            )}
            {(tab === "all" || tab === "upcoming") && (
              <Section
                title="Próximos"
                subtitle="Aún no han comenzado"
                accent="sky"
                matches={upcoming}
                emptyLabel={
                  hasSearch
                    ? "Ningún próximo partido coincide con tu búsqueda."
                    : "No hay partidos programados en este bloque."
                }
              />
            )}
            {(tab === "all" || tab === "finished") && (
              <Section
                title="Finalizados"
                subtitle="Resultados cerrados"
                accent="zinc"
                matches={finished}
                emptyLabel={
                  hasSearch
                    ? "Ningún partido finalizado coincide con tu búsqueda."
                    : "Ningún partido finalizado en esta consulta."
                }
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
