"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { LeagueCatalogEntry } from "@/lib/leagues/catalog";
import { foldText } from "@/lib/valueBets/leagueTiers";

type Accent = "cyan" | "emerald";

const ACCENT_STYLES: Record<
  Accent,
  { border: string; label: string; buttonSelected: string; inputRing: string; inputBorder: string }
> = {
  cyan: {
    border: "border-cyan-500/25",
    label: "text-cyan-400/80",
    buttonSelected: "bg-cyan-500/15 text-cyan-100",
    inputRing: "ring-cyan-500/30 focus:border-cyan-500/40",
    inputBorder: "hover:border-cyan-500/35",
  },
  emerald: {
    border: "border-emerald-500/25",
    label: "text-emerald-400/80",
    buttonSelected: "bg-emerald-500/15 text-emerald-100",
    inputRing: "ring-emerald-500/30 focus:border-emerald-500/40",
    inputBorder: "hover:border-emerald-500/35",
  },
};

type LeagueFilterBarProps = {
  accent?: Accent;
  totalFixtureCount: number;
  options: LeagueCatalogEntry[];
  selectedKey: string | null;
  onSelect: (key: string | null) => void;
  /** Texto auxiliar junto al título (p. ej. "12 competiciones"). */
  subtitle?: string;
};

export function LeagueFilterBar({
  accent = "cyan",
  totalFixtureCount,
  options,
  selectedKey,
  onSelect,
  subtitle,
}: LeagueFilterBarProps) {
  const styles = ACCENT_STYLES[accent];
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
          const option = options.find((x) => x.key === selectedKey);
          if (!option) {
            return "Liga —";
          }
          return `${option.label} (${option.fixtureCount})`;
        })();

  return (
    <div
      ref={rootRef}
      className={`sticky top-0 z-40 mb-4 rounded-xl border ${styles.border} bg-zinc-950/95 p-3 shadow-[0_12px_40px_-12px_rgba(0,0,0,0.85)] backdrop-blur-md sm:p-4`}
    >
      <div className="mb-2 flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-3">
        <p className={`text-[10px] font-semibold uppercase tracking-wide ${styles.label}`}>
          Filtro por liga
        </p>
        {subtitle ? <p className="text-[10px] text-zinc-500">{subtitle}</p> : null}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar por nombre de liga…"
          className={`min-h-[44px] min-w-0 flex-1 rounded-lg border border-white/15 bg-black/40 px-3 py-2.5 text-sm text-white outline-none placeholder:text-zinc-600 focus:ring-2 sm:min-h-0 ${styles.inputRing}`}
          aria-label="Buscar liga"
        />
        <div className="relative min-w-0 sm:min-w-[14rem] sm:max-w-[min(100%,20rem)]">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className={`flex min-h-[44px] w-full items-center justify-between gap-2 rounded-lg border border-white/15 bg-zinc-900/80 px-3 py-2.5 text-left text-sm font-medium text-zinc-100 transition ${styles.inputBorder} hover:bg-zinc-900 sm:min-h-0`}
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
                    selectedKey == null ? styles.buttonSelected : "text-zinc-200"
                  }`}
                >
                  <span className="truncate">Todas las ligas</span>
                  <span className="shrink-0 tabular-nums text-zinc-500">({totalFixtureCount})</span>
                </button>
              </li>
              {filteredOptions.map((option) => (
                <li key={option.key} role="presentation">
                  <button
                    type="button"
                    role="option"
                    aria-selected={selectedKey === option.key}
                    onClick={() => {
                      onSelect(option.key);
                      setOpen(false);
                    }}
                    className={`flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left text-sm transition hover:bg-white/5 ${
                      selectedKey === option.key ? styles.buttonSelected : "text-zinc-200"
                    }`}
                  >
                    <span className="min-w-0 flex-1 truncate" title={option.label}>
                      {option.label}
                    </span>
                    <span className="shrink-0 tabular-nums text-zinc-500">({option.fixtureCount})</span>
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
