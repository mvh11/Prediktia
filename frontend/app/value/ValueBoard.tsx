"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  buildFixtureValueGroups,
  classifyValuePick,
  compareFixtureGroupsEditorial,
  effectiveCountry,
  effectiveLeagueName,
  fetchValueBetsOnce,
  foldText,
  formatHeroPickPill,
  formatPickOutcomeLabel,
  getLeagueTierForPick,
  isCancelledOrPostponed,
  isLiveEstado,
  selectPickOfTheDay,
  type FixtureValueGroup,
  type ValueBetPick,
  type ValueBetsResponse,
} from "@/lib/valueBets";
import {
  valueGradeCardClasses,
  valueGradeEvCellClasses,
  valueGradeGlowBar,
  valueGradeHeroBadgeClasses,
  valueGradeShortLabel,
  valueGradeValueChipClasses,
  type ValueGrade,
} from "@/lib/valueBets/evPresentation";

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

function pct1(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

/** Clave estable por competición (catálogo dinámico / filtro). */
function leagueStableKey(pick: ValueBetPick): string {
  const id = pick.league_id ?? 0;
  if (id > 0) {
    return `id:${id}`;
  }
  const c = foldText(effectiveCountry(pick));
  const n = foldText(effectiveLeagueName(pick));
  const l = foldText(pick.liga);
  return `txt:${c}|${n}|${l}`;
}

function leagueDisplayLabel(pick: ValueBetPick): string {
  const raw = pick.liga.trim();
  if (raw) {
    return raw;
  }
  const name = effectiveLeagueName(pick).trim();
  const country = effectiveCountry(pick).trim();
  if (name && country) {
    return `${name} (${country})`;
  }
  return name || country || "—";
}

function gradeRowBadgeClass(grade: ValueGrade): string {
  switch (grade) {
    case "elite":
      return "bg-violet-500/15 text-violet-200 ring-1 ring-violet-400/25";
    case "high":
      return "bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-400/25";
    case "good":
      return "bg-sky-500/15 text-sky-200 ring-1 ring-sky-400/25";
    default:
      return "bg-orange-500/12 text-orange-200 ring-1 ring-orange-400/25";
  }
}

const API_SPORTS_TEAM_LOGO = (id: number) => `https://media.api-sports.io/football/teams/${id}.png`;

function TeamLine({
  teamId,
  name,
  featured = false,
}: {
  teamId?: number;
  name: string;
  featured?: boolean;
}) {
  const [logoFailed, setLogoFailed] = useState(false);
  const id = teamId ?? 0;
  const showLogo = id > 0 && !logoFailed;

  return (
    <div className="flex min-w-0 items-center gap-3 sm:gap-3.5">
      <div
        className={`relative flex shrink-0 items-center justify-center overflow-hidden rounded-xl bg-zinc-900/90 ring-1 ring-white/[0.07] ${
          featured ? "h-11 w-11 sm:h-12 sm:w-12" : "h-10 w-10 sm:h-11 sm:w-11"
        }`}
      >
        {showLogo ? (
          <img
            src={API_SPORTS_TEAM_LOGO(id)}
            alt=""
            width={48}
            height={48}
            className="h-full w-full object-contain p-1.5"
            loading="lazy"
            onError={() => setLogoFailed(true)}
          />
        ) : (
          <span className="select-none text-[11px] font-bold uppercase tracking-tighter text-zinc-500">
            {(name.trim().slice(0, 2) || "?").toUpperCase()}
          </span>
        )}
      </div>
      <span
        className={`min-w-0 truncate font-semibold tracking-tight text-white ${
          featured ? "text-lg sm:text-xl" : "text-base sm:text-lg"
        }`}
        title={name}
      >
        {name}
      </span>
    </div>
  );
}

function FixtureValueCard({ group, featured = false }: { group: FixtureValueGroup; featured?: boolean }) {
  const { hero, heroGrade, picks } = group;
  const cardRing = valueGradeCardClasses(heroGrade);
  const heroBadge = valueGradeHeroBadgeClasses(heroGrade);
  const evCell = valueGradeEvCellClasses(heroGrade);
  const barGradient = valueGradeGlowBar(heroGrade);
  const valueChip = valueGradeValueChipClasses(heroGrade);

  const featuredRing =
    featured === true
      ? "ring-2 ring-amber-400/45 shadow-[0_0_48px_-16px_rgba(251,191,36,0.28)]"
      : "";

  return (
    <details
      className={`group relative overflow-hidden rounded-2xl border backdrop-blur-sm transition-all duration-300 ease-out hover:-translate-y-0.5 hover:border-white/[0.12] hover:shadow-[0_20px_44px_-28px_rgba(0,0,0,0.88),0_0_0_1px_rgba(255,255,255,0.04)] open:border-white/[0.1] open:shadow-[0_24px_50px_-22px_rgba(0,0,0,0.9)] [&>summary::-webkit-details-marker]:hidden ${cardRing} ${featuredRing}`}
    >
      <div
        className={`pointer-events-none absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${barGradient}`}
        aria-hidden
      />

      <summary className="cursor-pointer list-none px-6 py-6 sm:px-8 sm:py-7">
        {featured && (
          <div className="mb-5 inline-flex items-center rounded-full border border-amber-400/40 bg-gradient-to-r from-amber-400/95 via-amber-500 to-orange-500 px-3 py-1 text-[9px] font-black uppercase tracking-[0.18em] text-black shadow-sm">
            Pick del día
          </div>
        )}

        <p className="line-clamp-1 text-[10px] font-medium uppercase tracking-[0.12em] text-zinc-500" title={hero.liga}>
          {hero.liga}
        </p>

        <div className="mt-5 flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between sm:gap-8">
          <div className={`min-w-0 flex-1 rounded-2xl px-4 py-4 sm:px-5 sm:py-5 ${evCell}`}>
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500/90">EV</p>
            <p
              className={`mt-1 font-black tabular-nums tracking-tight text-white ${
                featured ? "text-4xl sm:text-5xl" : "text-3xl sm:text-[2.75rem]"
              }`}
            >
              +{pct1(hero.ev)}
            </p>
            <p className="mt-2 text-sm tabular-nums text-zinc-400">@{hero.cuota.toFixed(2)}</p>
          </div>

          <div className="flex shrink-0 flex-row items-center gap-2 sm:flex-col sm:items-end sm:gap-2.5">
            <span
              className={`rounded-md px-2 py-1 text-center text-[9px] font-bold uppercase tracking-wide ${heroBadge}`}
            >
              {valueGradeShortLabel(heroGrade)}
            </span>
            <span
              className={`rounded px-1.5 py-0.5 text-[7px] font-semibold uppercase tracking-[0.12em] ${valueChip}`}
            >
              Value
            </span>
            <time
              className="text-[11px] tabular-nums text-zinc-500 sm:text-right"
              dateTime={hero.fecha}
            >
              {formatKickoff(hero.fecha)}
            </time>
          </div>
        </div>

        <div className="mt-6 space-y-3 border-t border-white/[0.06] pt-6">
          <TeamLine teamId={hero.team_home_id} name={hero.equipo_local} featured={featured} />
          <p className="pl-12 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600 sm:pl-14">vs</p>
          <TeamLine teamId={hero.team_away_id} name={hero.equipo_visitante} featured={featured} />
        </div>

        <div className="mt-6">
          <div className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.06] to-transparent px-4 py-3.5 text-sm font-medium leading-snug text-zinc-100 shadow-inner shadow-black/20 ring-1 ring-white/[0.04]">
            {formatHeroPickPill(hero)}
          </div>
        </div>

        <p className="mt-5 line-clamp-1 text-xs text-zinc-500" title={hero.estado_partido}>
          {hero.estado_partido}
        </p>

        <div className="mt-5 flex items-center justify-between border-t border-white/[0.06] pt-4 text-left">
          <span className="text-[11px] font-medium text-zinc-500">
            Mercados <span className="tabular-nums text-zinc-400">({picks.length})</span>
          </span>
          <span
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-zinc-400 transition-transform duration-300 group-open:rotate-180"
            aria-hidden
          >
            <span className="text-[10px]">▼</span>
          </span>
        </div>
      </summary>

      <div className="border-t border-white/[0.06] bg-black/20 px-6 pb-6 pt-2 sm:px-8 sm:pb-7">
        <div className="overflow-x-auto rounded-xl ring-1 ring-white/[0.06]">
          <table className="w-full min-w-[28rem] text-left text-sm">
            <thead className="bg-white/[0.03] text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
              <tr>
                <th className="px-4 py-3">Mercado</th>
                <th className="px-4 py-3">Selección</th>
                <th className="px-4 py-3 text-right tabular-nums">Cuota</th>
                <th className="px-4 py-3 text-right tabular-nums">Prob.</th>
                <th className="px-4 py-3 text-right tabular-nums">EV</th>
                <th className="px-4 py-3 text-center">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.05]">
              {picks.map((p) => {
                const g = classifyValuePick(p);
                return (
                  <tr
                    key={`${p.fixture_id}-${p.mercado}-${p.pick}`}
                    className="bg-transparent transition-colors hover:bg-white/[0.02]"
                  >
                    <td className="px-4 py-3 text-zinc-400">{p.mercado}</td>
                    <td className="px-4 py-3 font-medium text-zinc-100">{formatPickOutcomeLabel(p)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-white">{p.cuota.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-cyan-200/85">{pct1(p.probabilidad)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-emerald-200/90">+{pct1(p.ev)}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block rounded-md px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide ${gradeRowBadgeClass(g)}`}
                      >
                        {valueGradeShortLabel(g)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </details>
  );
}

type LeagueCatalogEntry = { key: string; label: string; fixtureCount: number };

function StickyLeagueFilterBar({
  totalFixtureCount,
  options,
  selectedKey,
  onSelect,
  leagueCount,
}: {
  totalFixtureCount: number;
  options: LeagueCatalogEntry[];
  selectedKey: string | null;
  onSelect: (key: string | null) => void;
  leagueCount: number;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const close = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const filteredOptions = useMemo(() => {
    const q = foldText(query);
    if (!q) {
      return options;
    }
    return options.filter((o) => foldText(o.label).includes(q) || foldText(o.key).includes(q));
  }, [options, query]);

  const currentLabel =
    selectedKey == null
      ? `Todas las ligas (${totalFixtureCount})`
      : (() => {
          const o = options.find((x) => x.key === selectedKey);
          if (!o) {
            return "Liga —";
          }
          return `${o.label} (${o.fixtureCount})`;
        })();

  return (
    <div
      ref={rootRef}
      className="sticky top-0 z-40 mb-4 rounded-xl border border-cyan-500/25 bg-zinc-950/95 p-3 shadow-[0_12px_40px_-12px_rgba(0,0,0,0.85)] backdrop-blur-md sm:p-4"
    >
      <div className="mb-2 flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-3">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-cyan-400/80">Filtro por liga</p>
        <p className="text-[10px] text-zinc-500">
          <span className="font-mono tabular-nums text-zinc-400">{leagueCount}</span> competiciones con picks
        </p>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar por nombre de liga…"
          className="min-h-[44px] min-w-0 flex-1 rounded-lg border border-white/15 bg-black/40 px-3 py-2.5 text-sm text-white outline-none ring-cyan-500/30 placeholder:text-zinc-600 focus:border-cyan-500/40 focus:ring-2 sm:min-h-0"
          aria-label="Buscar liga"
        />
        <div className="relative min-w-0 sm:min-w-[14rem] sm:max-w-[min(100%,20rem)]">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex min-h-[44px] w-full items-center justify-between gap-2 rounded-lg border border-white/15 bg-zinc-900/80 px-3 py-2.5 text-left text-sm font-medium text-zinc-100 transition hover:border-cyan-500/35 hover:bg-zinc-900 sm:min-h-0"
            aria-expanded={open}
            aria-haspopup="listbox"
          >
            <span className="truncate">{currentLabel}</span>
            <span className="shrink-0 text-zinc-500" aria-hidden>
              {open ? "▲" : "▼"}
            </span>
          </button>
          {open && (
            <ul
              className="absolute left-0 right-0 z-50 mt-1 max-h-[min(50vh,16rem)] overflow-y-auto rounded-lg border border-white/15 bg-zinc-950 py-1 shadow-xl ring-1 ring-black/40 sm:max-h-72"
              role="listbox"
            >
              <li role="presentation">
                <button
                  type="button"
                  role="option"
                  aria-selected={selectedKey == null}
                  onClick={() => {
                    onSelect(null);
                    setOpen(false);
                  }}
                  className={`flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left text-sm transition hover:bg-white/5 ${
                    selectedKey == null ? "bg-cyan-500/15 text-cyan-100" : "text-zinc-200"
                  }`}
                >
                  <span className="truncate">Todas las ligas</span>
                  <span className="shrink-0 tabular-nums text-zinc-500">({totalFixtureCount})</span>
                </button>
              </li>
              {filteredOptions.map((o) => (
                <li key={o.key} role="presentation">
                  <button
                    type="button"
                    role="option"
                    aria-selected={selectedKey === o.key}
                    onClick={() => {
                      onSelect(o.key);
                      setOpen(false);
                    }}
                    className={`flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left text-sm transition hover:bg-white/5 ${
                      selectedKey === o.key ? "bg-cyan-500/15 text-cyan-100" : "text-zinc-200"
                    }`}
                  >
                    <span className="min-w-0 flex-1 truncate" title={o.label}>
                      {o.label}
                    </span>
                    <span className="shrink-0 tabular-nums text-zinc-500">({o.fixtureCount})</span>
                  </button>
                </li>
              ))}
              {filteredOptions.length === 0 && (
                <li className="px-3 py-4 text-center text-xs text-zinc-500">Sin coincidencias</li>
              )}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="animate-pulse overflow-hidden rounded-2xl border border-white/10 bg-zinc-900/40 p-5 sm:p-6"
        >
          <div className="mb-4 flex justify-between gap-3">
            <div className="flex-1 space-y-2">
              <div className="h-3 w-24 rounded bg-zinc-800" />
              <div className="h-6 w-full max-w-[14rem] rounded bg-zinc-800" />
            </div>
            <div className="h-14 w-[7.5rem] shrink-0 self-start rounded-lg bg-zinc-800 sm:h-16 sm:w-32" />
          </div>
          <div className="mb-4 h-4 w-full rounded bg-zinc-800/80" />
          <div className="mb-4 h-14 rounded-xl bg-zinc-800/60" />
          <div className="h-16 rounded-xl bg-zinc-800/50" />
        </div>
      ))}
    </div>
  );
}

export function ValueBoard() {
  const [payload, setPayload] = useState<ValueBetsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(20);
  const [showExcludedStatuses, setShowExcludedStatuses] = useState(false);
  const [showMinorLeagues, setShowMinorLeagues] = useState(false);
  const [selectedLeagueKey, setSelectedLeagueKey] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchValueBetsOnce()
      .then((data) => {
        if (!cancelled) {
          setPayload(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Error desconocido");
        }
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

  useEffect(() => {
    setVisibleCount(20);
  }, [payload, showExcludedStatuses, showMinorLeagues, selectedLeagueKey]);

  const rawPicks = useMemo(() => payload?.picks ?? [], [payload]);

  const excludedCancelledCount = useMemo(
    () => rawPicks.filter((p) => isCancelledOrPostponed(p.estado_partido)).length,
    [rawPicks],
  );

  const tierDCount = useMemo(
    () => rawPicks.filter((p) => getLeagueTierForPick(p) === "D").length,
    [rawPicks],
  );

  const picksAfterCancelFilter = useMemo(
    () => rawPicks.filter((p) => showExcludedStatuses || !isCancelledOrPostponed(p.estado_partido)),
    [rawPicks, showExcludedStatuses],
  );

  const leagueCatalog = useMemo((): LeagueCatalogEntry[] => {
    const map = new Map<string, { label: string; fixtures: Set<number> }>();
    for (const p of picksAfterCancelFilter) {
      const key = leagueStableKey(p);
      let row = map.get(key);
      if (!row) {
        row = { label: leagueDisplayLabel(p), fixtures: new Set() };
        map.set(key, row);
      }
      row.fixtures.add(p.fixture_id);
    }
    return [...map.entries()]
      .map(([key, v]) => ({
        key,
        label: v.label,
        fixtureCount: v.fixtures.size,
      }))
      .sort((a, b) => b.fixtureCount - a.fixtureCount || a.label.localeCompare(b.label, "es"));
  }, [picksAfterCancelFilter]);

  const totalCatalogFixtures = useMemo(() => {
    const s = new Set<number>();
    for (const p of picksAfterCancelFilter) {
      s.add(p.fixture_id);
    }
    return s.size;
  }, [picksAfterCancelFilter]);

  useEffect(() => {
    if (selectedLeagueKey == null) {
      return;
    }
    if (!leagueCatalog.some((o) => o.key === selectedLeagueKey)) {
      setSelectedLeagueKey(null);
    }
  }, [leagueCatalog, selectedLeagueKey]);

  const onlyCancelledHidden =
    picksAfterCancelFilter.length === 0 && excludedCancelledCount > 0 && !showExcludedStatuses;

  const onlyTierDHidden =
    picksAfterCancelFilter.length > 0 &&
    picksAfterCancelFilter.every((p) => getLeagueTierForPick(p) === "D") &&
    !showMinorLeagues;

  const rankedFixtures = useMemo((): FixtureValueGroup[] => {
    const filtered = rawPicks.filter((p) => {
      if (!(showExcludedStatuses || !isCancelledOrPostponed(p.estado_partido))) {
        return false;
      }
      if (!showMinorLeagues && getLeagueTierForPick(p) === "D") {
        return false;
      }
      return true;
    });
    const groups = buildFixtureValueGroups(filtered);
    return [...groups].sort(compareFixtureGroupsEditorial);
  }, [rawPicks, showExcludedStatuses, showMinorLeagues]);

  const displayRankedFixtures = useMemo(() => {
    if (selectedLeagueKey == null) {
      return rankedFixtures;
    }
    return rankedFixtures.filter((g) => leagueStableKey(g.hero) === selectedLeagueKey);
  }, [rankedFixtures, selectedLeagueKey]);

  const pickOfTheDayGroup = useMemo(() => selectPickOfTheDay(displayRankedFixtures), [displayRankedFixtures]);

  const gridFixtures = useMemo(() => {
    if (!pickOfTheDayGroup) {
      return displayRankedFixtures;
    }
    return displayRankedFixtures.filter((g) => g.fixture_id !== pickOfTheDayGroup.fixture_id);
  }, [displayRankedFixtures, pickOfTheDayGroup]);

  const selectedLeagueCatalog = useMemo(
    () => (selectedLeagueKey == null ? null : leagueCatalog.find((o) => o.key === selectedLeagueKey) ?? null),
    [leagueCatalog, selectedLeagueKey],
  );

  const fixturesInRankedForSelectedLeague = useMemo(() => {
    if (selectedLeagueKey == null) {
      return 0;
    }
    return rankedFixtures.filter((g) => leagueStableKey(g.hero) === selectedLeagueKey).length;
  }, [rankedFixtures, selectedLeagueKey]);

  const stats = useMemo(() => {
    const total = displayRankedFixtures.length;
    const avgEv =
      total === 0 ? 0 : displayRankedFixtures.reduce((s, g) => s + g.hero.ev, 0) / total;
    const live = displayRankedFixtures.filter((g) => isLiveEstado(g.hero.estado_partido)).length;
    const highElite = displayRankedFixtures.filter(
      (g) => g.heroGrade === "high" || g.heroGrade === "elite",
    ).length;
    const lines = displayRankedFixtures.reduce((s, g) => s + g.picks.length, 0);
    return { total, avgEv, live, highElite, lines };
  }, [displayRankedFixtures]);

  const visibleRows = useMemo(
    () => gridFixtures.slice(0, visibleCount),
    [gridFixtures, visibleCount],
  );
  const canLoadMore = visibleCount < gridFixtures.length;

  return (
    <div className="min-h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-cyan-950/35 via-zinc-950 to-black pb-16 pt-8 text-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <header className="mb-10 text-center sm:text-left">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400/85">Prediktia</p>
          <h1 className="mt-2 bg-gradient-to-r from-white via-zinc-100 to-zinc-400 bg-clip-text text-3xl font-black tracking-tight text-transparent sm:text-4xl">
            Apuestas con valor (EV+)
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-sm text-zinc-500 sm:mx-0">
            Un partido = una card; arriba, cuando hay candidatos, un <span className="text-zinc-400">Pick del día</span>{" "}
            premium (Europa top o LATAM). Orden editorial: prestigio (Europa top, luego LATAM principal, luego el
            resto), luego score (liquidez, mercado, EV acotado). El mock limita EV en doble oportunidad y favoritos cortos para que el feed se vea
            creíble.
          </p>
        </header>

        {!loading && !error && payload && rawPicks.length > 0 && (
          <StickyLeagueFilterBar
            totalFixtureCount={totalCatalogFixtures}
            options={leagueCatalog}
            selectedKey={selectedLeagueKey}
            onSelect={setSelectedLeagueKey}
            leagueCount={leagueCatalog.length}
          />
        )}

        {loading && <SkeletonGrid />}

        {error && !loading && (
          <div
            className="mx-auto max-w-xl rounded-2xl border border-red-500/35 bg-red-950/40 px-5 py-6 text-center shadow-xl shadow-red-950/30"
            role="alert"
          >
            <p className="text-sm font-semibold text-red-100">No se pudieron cargar las apuestas con valor</p>
            <p className="mt-2 text-sm text-red-200/90">{error}</p>
            <p className="mt-4 text-xs text-red-300/70">
              Comprueba que el backend esté en marcha y que la clave de API-Football sea válida.
            </p>
          </div>
        )}

        {!loading && !error && payload && rawPicks.length === 0 && (
          <div className="mx-auto max-w-lg rounded-2xl border border-dashed border-zinc-700 bg-zinc-900/35 px-6 py-14 text-center">
            <p className="text-lg font-semibold text-zinc-200">Sin picks EV+ hoy</p>
            <p className="mt-2 text-sm text-zinc-500">
              No hay líneas mock que superen el umbral de EV positivo para los partidos de la fecha{" "}
              <span className="tabular-nums text-zinc-400">{payload.date}</span>. Prueba más tarde o con otra
              fecha cuando el calendario tenga más volumen.
            </p>
          </div>
        )}

        {!loading && !error && payload && rawPicks.length > 0 && rankedFixtures.length === 0 && !selectedLeagueKey && (
          <div className="mx-auto max-w-lg rounded-2xl border border-dashed border-zinc-700 bg-zinc-900/35 px-6 py-14 text-center">
            <p className="text-lg font-semibold text-zinc-200">Sin partidos visibles</p>
            {onlyCancelledHidden ? (
              <p className="mt-2 text-sm text-zinc-500">
                Todos los picks cargados corresponden a partidos cancelados o postergados (CANC / PST), ocultos por
                defecto. Usa el botón del resumen para mostrarlos.
              </p>
            ) : onlyTierDHidden ? (
              <div className="mt-4 space-y-4">
                <p className="text-sm text-zinc-500">
                  Solo hay picks en <span className="font-medium text-zinc-400">ligas menores (tier D)</span>:
                  juveniles, reservas, femenino no élite, regionales u otras señales de baja confiabilidad. No se
                  muestran en la vista principal para mantener la lista premium.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setShowMinorLeagues(true);
                    setVisibleCount(20);
                  }}
                  className="rounded-xl border border-amber-500/35 bg-amber-500/10 px-5 py-2.5 text-sm font-semibold text-amber-100 transition hover:border-amber-400/50 hover:bg-amber-500/15"
                >
                  Mostrar {tierDCount} picks de ligas menores
                </button>
              </div>
            ) : (
              <p className="mt-2 text-sm text-zinc-500">
                No quedan picks que cumplan los filtros actuales. Prueba a mostrar cancelados o ligas menores desde
                el resumen.
              </p>
            )}
          </div>
        )}

        {!loading &&
          !error &&
          payload &&
          rawPicks.length > 0 &&
          selectedLeagueKey &&
          displayRankedFixtures.length === 0 && (
            <div className="mx-auto max-w-lg rounded-2xl border border-dashed border-amber-500/35 bg-zinc-900/50 px-6 py-12 text-center">
              <p className="text-lg font-semibold text-zinc-100">Sin partidos para esta liga</p>
              <p className="mt-2 text-sm text-zinc-400">
                Filtro:{" "}
                <span className="font-medium text-cyan-200/95">
                  {selectedLeagueCatalog?.label ?? selectedLeagueKey}
                </span>
              </p>
              {(selectedLeagueCatalog?.fixtureCount ?? 0) > 0 && fixturesInRankedForSelectedLeague === 0 ? (
                <p className="mt-4 text-sm leading-relaxed text-zinc-500">
                  En los datos cargados hay{" "}
                  <span className="font-mono tabular-nums text-zinc-300">{selectedLeagueCatalog?.fixtureCount}</span>{" "}
                  partido{(selectedLeagueCatalog?.fixtureCount ?? 0) === 1 ? "" : "s"} de esta competición (sin
                  cancelados{showExcludedStatuses ? "" : " ocultos"}), pero{" "}
                  <span className="text-zinc-400">ninguno aparece en el feed actual</span>: revisa{" "}
                  <span className="text-amber-200/90">ligas menores (tier D)</span> o cancelados/postergados en el
                  resumen cuando haya partidos visibles globales.
                </p>
              ) : rankedFixtures.length > 0 ? (
                <p className="mt-4 text-sm text-zinc-500">
                  No hay partidos de esta liga entre los que ya pasan el feed editorial y los filtros de tier. Prueba
                  otra competición o vuelve a <span className="text-zinc-400">Todas las ligas</span>.
                </p>
              ) : (
                <p className="mt-4 text-sm text-zinc-500">
                  El feed global está vacío con los filtros actuales; al activar más partidos, deberían aparecer aquí
                  si la API incluye esta liga.
                </p>
              )}
              <button
                type="button"
                onClick={() => {
                  setSelectedLeagueKey(null);
                  setVisibleCount(20);
                }}
                className="mt-6 rounded-xl border border-cyan-500/35 bg-cyan-500/10 px-5 py-2.5 text-sm font-semibold text-cyan-100 transition hover:border-cyan-400/50 hover:bg-cyan-500/15"
              >
                Ver todas las ligas
              </button>
            </div>
          )}

        {!loading && !error && payload && rawPicks.length > 0 && displayRankedFixtures.length > 0 && (
          <>
            <div className="mb-6 rounded-2xl border border-white/10 bg-zinc-900/50 p-4 sm:p-5">
              <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  Resumen · fecha <span className="tabular-nums text-zinc-400">{payload.date}</span>
                  {selectedLeagueKey ? (
                    <span className="ml-2 text-cyan-400/90">· filtro de liga activo</span>
                  ) : null}
                </p>
                <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-end sm:gap-2">
                  {excludedCancelledCount > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        setShowExcludedStatuses((v) => !v);
                        setVisibleCount(20);
                      }}
                      className="self-start rounded-lg border border-white/10 bg-zinc-950/60 px-3 py-2 text-left text-xs font-medium text-cyan-300/95 transition hover:border-cyan-500/35 hover:bg-zinc-900 sm:self-auto"
                    >
                      {showExcludedStatuses
                        ? "Ocultar cancelados / postergados"
                        : `Mostrar ${excludedCancelledCount} cancelados / postergados`}
                    </button>
                  )}
                  {tierDCount > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        setShowMinorLeagues((v) => !v);
                        setVisibleCount(20);
                      }}
                      className="self-start rounded-lg border border-white/10 bg-zinc-950/60 px-3 py-2 text-left text-xs font-medium text-amber-200/95 transition hover:border-amber-500/35 hover:bg-zinc-900 sm:self-auto"
                    >
                      {showMinorLeagues
                        ? "Ocultar ligas menores (tier D)"
                        : `Mostrar ${tierDCount} ligas menores (tier D)`}
                    </button>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-xl border border-white/10 bg-black/30 px-3 py-3 sm:px-4">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500 sm:text-xs">
                    Partidos
                  </p>
                  <p className="mt-1 text-2xl font-black tabular-nums text-white">{stats.total}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/30 px-3 py-3 sm:px-4">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500 sm:text-xs">
                    Líneas EV+
                  </p>
                  <p className="mt-1 text-2xl font-black tabular-nums text-zinc-200">{stats.lines}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/30 px-3 py-3 sm:px-4">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500 sm:text-xs">
                    EV medio (destacado)
                  </p>
                  <p className="mt-1 text-2xl font-black tabular-nums text-emerald-300/95">+{pct1(stats.avgEv)}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/30 px-3 py-3 sm:px-4">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500 sm:text-xs">
                    LIVE · HIGH+
                  </p>
                  <p className="mt-1 text-xl font-black tabular-nums text-sky-300/95">
                    {stats.live}{" "}
                    <span className="text-zinc-600">·</span>{" "}
                    <span className="text-amber-200/95">{stats.highElite}</span>
                  </p>
                </div>
              </div>
              <p className="mt-3 text-[11px] leading-relaxed text-zinc-500 sm:text-xs">
                Mostrando {visibleRows.length} de {gridFixtures.length} partidos en lista
                {pickOfTheDayGroup ? " (más el destacado arriba)" : ""}
                {selectedLeagueKey ? " · solo la liga seleccionada" : ""}: orden editorial (región, prestigio, score,
                liquidez, EV). Doble oportunidad y favoritos llevan EV mock más contenido.
              </p>
            </div>

            {pickOfTheDayGroup && (
              <section className="mb-10" aria-labelledby="pick-dia-heading">
                <div className="mb-4">
                  <h2
                    id="pick-dia-heading"
                    className="text-sm font-black uppercase tracking-[0.22em] text-amber-200/95"
                  >
                    Destacado
                  </h2>
                  <p className="mt-1 max-w-2xl text-xs text-zinc-500">
                    Pick del día entre los partidos visibles
                    {selectedLeagueKey ? " (solo liga seleccionada)" : ""}: competición top o LATAM principal, mercado
                    confiable, cuota en rango líquido y EV contenido.
                  </p>
                </div>
                <div className="rounded-3xl border border-amber-500/30 bg-gradient-to-b from-amber-500/14 via-zinc-900/40 to-zinc-950/90 p-1.5 shadow-[0_0_60px_-18px_rgba(245,158,11,0.28)] sm:p-2">
                  <FixtureValueCard group={pickOfTheDayGroup} featured />
                </div>
              </section>
            )}

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {visibleRows.map((group) => (
                <FixtureValueCard key={group.fixture_id} group={group} />
              ))}
            </div>

            {canLoadMore && (
              <div className="mt-8 flex justify-center">
                <button
                  type="button"
                  onClick={() => setVisibleCount((c) => Math.min(c + 20, gridFixtures.length))}
                  className="rounded-xl border border-emerald-500/35 bg-emerald-500/10 px-6 py-3 text-sm font-semibold text-emerald-200 transition hover:border-emerald-400/50 hover:bg-emerald-500/15"
                >
                  Cargar más partidos ({gridFixtures.length - visibleCount} restantes)
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
