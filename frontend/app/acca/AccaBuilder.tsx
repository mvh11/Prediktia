"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchAccaHistory,
  fetchSmartAcca,
  type AccaHistoryListResponse,
  type AccaRiskLevel,
  type SmartAccaResponse,
} from "@/lib/acca";

const RISK_OPTIONS: { id: AccaRiskLevel; label: string; hint: string }[] = [
  { id: "low", label: "Bajo", hint: "2–3 picks · alta probabilidad" },
  { id: "medium", label: "Medio", hint: "3–5 picks · EV equilibrado" },
  { id: "high", label: "Alto", hint: "4–6 picks · edge alto" },
  { id: "extreme", label: "Muy alto", hint: "5+ picks · máxima volatilidad" },
];

function riskTheme(risk: AccaRiskLevel) {
  switch (risk) {
    case "low":
      return {
        ring: "ring-sky-500/40",
        glow: "shadow-[0_0_48px_-12px_rgba(56,189,248,0.35)]",
        bar: "from-sky-400 to-cyan-500",
        badge: "bg-sky-500/20 text-sky-100 ring-sky-400/35",
        accent: "text-sky-300",
        panel: "border-sky-500/25 bg-gradient-to-b from-sky-500/[0.08] to-zinc-950/60",
      };
    case "medium":
      return {
        ring: "ring-emerald-500/40",
        glow: "shadow-[0_0_48px_-12px_rgba(52,211,153,0.32)]",
        bar: "from-emerald-400 to-teal-500",
        badge: "bg-emerald-500/20 text-emerald-100 ring-emerald-400/35",
        accent: "text-emerald-300",
        panel: "border-emerald-500/25 bg-gradient-to-b from-emerald-500/[0.08] to-zinc-950/60",
      };
    case "high":
      return {
        ring: "ring-amber-500/45",
        glow: "shadow-[0_0_52px_-12px_rgba(245,158,11,0.38)]",
        bar: "from-amber-400 to-orange-500",
        badge: "bg-amber-500/20 text-amber-100 ring-amber-400/35",
        accent: "text-amber-300",
        panel: "border-amber-500/25 bg-gradient-to-b from-amber-500/[0.08] to-zinc-950/60",
      };
    default:
      return {
        ring: "ring-rose-500/45",
        glow: "shadow-[0_0_56px_-10px_rgba(244,63,94,0.42)]",
        bar: "from-rose-500 to-fuchsia-600",
        badge: "bg-rose-500/20 text-rose-100 ring-rose-400/35",
        accent: "text-rose-300",
        panel: "border-rose-500/25 bg-gradient-to-b from-rose-500/[0.08] to-zinc-950/60",
      };
  }
}

function pctProb(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function formatKickoffLabel(m: number | null | undefined): string {
  if (m == null || Number.isNaN(m)) return "Kickoff —";
  if (m < 0) return "Kickoff (UTC) ya pasado";
  if (m < 120) return `Kickoff en ~${m} min (UTC)`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  if (r === 0) return `Kickoff en ~${h} h (UTC)`;
  return `Kickoff en ~${h}h ${r}m (UTC)`;
}

function ScoreMeter({
  label,
  value,
  gradient,
}: {
  label: string;
  value: number;
  gradient: string;
}) {
  const w = Math.max(4, Math.min(100, value));
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
        <span>{label}</span>
        <span className="tabular-nums text-zinc-300">{value.toFixed(0)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-zinc-800/80 ring-1 ring-white/5">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${gradient} transition-all duration-700 ease-out`}
          style={{ width: `${w}%` }}
        />
      </div>
    </div>
  );
}

export function AccaBuilder() {
  const [risk, setRisk] = useState<AccaRiskLevel>("medium");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SmartAccaResponse | null>(null);
  const [history, setHistory] = useState<AccaHistoryListResponse | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const theme = riskTheme(result?.risk ?? risk);

  const loadHistory = useCallback(async () => {
    try {
      const h = await fetchAccaHistory(25);
      setHistory(h);
      setHistoryError(null);
    } catch {
      setHistory(null);
      setHistoryError("No se pudo cargar el historial desde la API.");
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSmartAcca(risk);
      setResult(data);
      void loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al generar ACCA");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [risk, loadHistory]);

  return (
    <div className="min-h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-violet-950/30 via-zinc-950 to-black pb-20 pt-8 text-white">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <header className="mb-10 text-center sm:text-left">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-400/85">
            Prediktia Intelligence
          </p>
          <h1 className="mt-2 bg-gradient-to-r from-white via-zinc-100 to-zinc-400 bg-clip-text text-3xl font-black tracking-tight text-transparent sm:text-4xl">
            Smart ACCA Builder
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-sm text-zinc-500 sm:mx-0">
            Poisson + EV real vs cuota · combinadas distintas por perfil de riesgo. Elige bajo, medio, alto o
            muy alto y regenera.
          </p>
        </header>

        <section className="mb-8 rounded-2xl border border-white/10 bg-zinc-900/50 p-5 backdrop-blur-sm sm:p-6">
          <p className="mb-4 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
            Perfil de riesgo
          </p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {RISK_OPTIONS.map((opt) => {
              const active = risk === opt.id;
              const t = riskTheme(opt.id);
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setRisk(opt.id)}
                  className={[
                    "rounded-xl border px-3 py-3 text-left transition-all duration-300",
                    active
                      ? `${t.ring} ring-2 ${t.panel} ${t.glow}`
                      : "border-white/10 bg-zinc-950/40 hover:border-white/20",
                  ].join(" ")}
                >
                  <span className={`text-sm font-bold ${active ? "text-white" : "text-zinc-300"}`}>
                    {opt.label}
                  </span>
                  <span className="mt-1 block text-[10px] leading-snug text-zinc-500">{opt.hint}</span>
                </button>
              );
            })}
          </div>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={() => void generate()}
              disabled={loading}
              className="group relative overflow-hidden rounded-xl bg-gradient-to-r from-violet-500 via-fuchsia-500 to-violet-600 px-6 py-3.5 text-sm font-bold text-white shadow-lg shadow-violet-900/40 transition hover:shadow-violet-800/50 disabled:opacity-60"
            >
              <span className="relative z-10 flex items-center justify-center gap-2">
                {loading ? "Generando…" : "Generar combinada ✨"}
              </span>
              <span
                className="pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full"
                aria-hidden
              />
            </button>
            <p className="text-xs text-zinc-500">
              Motor <span className="font-mono text-zinc-400">poisson-v1+ev-v1</span>
            </p>
          </div>
        </section>

        {error && (
          <div className="mb-6 rounded-xl border border-red-500/35 bg-red-950/40 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        {result && (
          <div
            className={`overflow-hidden rounded-2xl border transition-all duration-500 ${theme.panel} ${theme.glow}`}
          >
            <div className={`h-1 bg-gradient-to-r ${theme.bar}`} aria-hidden />

            <div className="p-6 sm:p-8">
              <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
                <div>
                  <span className={`inline-flex rounded-md px-2 py-1 text-[10px] font-bold uppercase ring-1 ${theme.badge}`}>
                    Riesgo {result.risk_label}
                  </span>
                  <p className="mt-3 text-4xl font-black tabular-nums tracking-tight text-white sm:text-5xl">
                    @{result.total_odds.toFixed(2)}
                  </p>
                  <p className="mt-1 text-sm text-zinc-400">
                    Cuota combinada · objetivo {result.profile.target_odds_range}
                  </p>
                  <p className="mt-2 text-sm text-zinc-300">
                    Combinada generada para los partidos del{" "}
                    <span className="font-semibold text-white">
                      {result.meta.resolved_date ?? result.date}
                    </span>
                  </p>
                  {result.meta.auto_shifted_date ? (
                    <p className="mt-1 max-w-xl text-xs leading-snug text-zinc-500">
                      El día UTC actual no tenía partidos pendientes (pre-partido); se usó la siguiente fecha con
                      fixtures válidos.
                    </p>
                  ) : null}
                  {result.acca_id && (
                    <p className="mt-2 font-mono text-[10px] text-zinc-600">
                      ID persistido · {result.acca_id}
                    </p>
                  )}
                </div>
                <div className="text-right">
                  <p className={`text-2xl font-black tabular-nums ${theme.accent}`}>
                    +{result.combined_ev_pct.toFixed(1)}%
                  </p>
                  <p className="text-[10px] uppercase tracking-wide text-zinc-500">EV combinado</p>
                  <p className="mt-2 text-sm tabular-nums text-zinc-400">
                    P ≈ {pctProb(result.combined_probability)}
                  </p>
                </div>
              </div>

              <div className="mb-8 grid gap-4 sm:grid-cols-3">
                <ScoreMeter label="Confianza" value={result.confidence_score} gradient={theme.bar} />
                <ScoreMeter label="Riesgo" value={result.risk_score} gradient="from-orange-500 to-rose-500" />
                <ScoreMeter
                  label="Volatilidad"
                  value={result.volatility_score}
                  gradient="from-amber-500 to-orange-600"
                />
              </div>

              {result.message && (
                <p className="mb-6 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-100/90">
                  {result.message}
                </p>
              )}

              <p className="mb-4 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                Picks incluidos ({result.pick_count})
              </p>
              <ul className="space-y-3">
                {result.picks.map((p) => (
                  <li
                    key={`${p.fixture_id}-${p.mercado}-${p.pick}`}
                    className="rounded-xl border border-white/[0.08] bg-black/30 p-4 transition hover:border-white/15"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-[10px] font-medium uppercase tracking-wide text-zinc-500">{p.liga}</p>
                        <p className="mt-1 font-semibold text-white">
                          {p.equipo_local}
                          <span className="mx-1.5 font-normal text-zinc-600">vs</span>
                          {p.equipo_visitante}
                        </p>
                        <p className="mt-2 inline-flex rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-1 text-xs text-zinc-200">
                          {p.mercado} · {p.pick}
                        </p>
                        <p className="mt-2 text-[10px] tabular-nums text-zinc-500">{formatKickoffLabel(p.kickoff_in_minutes)}</p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-1 text-right">
                        <span className="text-lg font-black tabular-nums text-white">@{p.cuota.toFixed(2)}</span>
                        <span className="text-xs font-semibold tabular-nums text-emerald-300/95">
                          EV +{p.ev_pct.toFixed(1)}%
                        </span>
                        <span className="text-[10px] tabular-nums text-zinc-500">
                          Conf. {p.confidence_pct.toFixed(0)}% · edge {p.edge_pct.toFixed(1)}%
                        </span>
                        <span className="text-[9px] uppercase text-zinc-600">{p.odds_source}</span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>

              <p className="mt-6 text-[11px] leading-relaxed text-zinc-600">
                Pool {result.meta.candidates_pool_size} candidatos · {result.meta.eligible_after_filters} elegibles ·{" "}
                {result.meta.bookmaker_odds_picks} con cuota bookmaker.
                {typeof result.meta.fixtures_upstream_total === "number" &&
                  typeof result.meta.fixtures_after_schedule_filter === "number" && (
                    <>
                      {" "}
                      Calendario: {result.meta.fixtures_after_schedule_filter} partidos pre-partido (UTC) de{" "}
                      {result.meta.fixtures_upstream_total} recibidos upstream.
                    </>
                  )}{" "}
                {result.meta.independence_assumption}
              </p>
            </div>
          </div>
        )}

        <section className="mt-12 rounded-2xl border border-white/10 bg-zinc-900/40 p-5 backdrop-blur-sm sm:p-6">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-400/80">Historial IA</p>
              <h2 className="mt-1 text-lg font-bold text-white">Combinadas generadas</h2>
              <p className="mt-1 text-xs text-zinc-500">
                Persistencia PostgreSQL: ROI y resultado cuando exista liquidación automática.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void loadHistory()}
              className="rounded-lg border border-white/15 bg-white/[0.04] px-3 py-1.5 text-xs font-semibold text-zinc-200 transition hover:border-white/25"
            >
              Actualizar
            </button>
          </div>
          {historyError && (
            <p className="mb-3 rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/90">
              {historyError}
            </p>
          )}
          {!history && !historyError && <p className="text-sm text-zinc-500">Cargando historial…</p>}
          {history && !history.database_configured && (
            <p className="text-sm text-zinc-500">
              La base de datos no está configurada en el backend. Define{" "}
              <span className="font-mono text-zinc-400">DATABASE_URL</span> y ejecuta migraciones Alembic para activar
              el historial.
            </p>
          )}
          {history && history.database_configured && history.items.length === 0 && (
            <p className="text-sm text-zinc-500">Aún no hay combinadas guardadas. Genera una ACCA con la API conectada a PostgreSQL.</p>
          )}
          {history && history.items.length > 0 && (
            <ul className="divide-y divide-white/[0.06] rounded-xl border border-white/[0.06] bg-black/25">
              {history.items.map((h) => (
                <li key={h.acca_id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm">
                  <div className="min-w-0">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                      {h.date || "—"} · {h.risk_label}
                    </p>
                    <p className="mt-0.5 truncate font-mono text-[10px] text-zinc-600">{h.acca_id}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-right tabular-nums">
                    <div>
                      <p className="text-xs font-bold text-white">@{h.total_odds.toFixed(2)}</p>
                      <p className="text-[10px] text-zinc-500">{h.pick_count} picks</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-emerald-300/90">+{h.combined_ev_pct.toFixed(1)}% EV</p>
                      <p className="text-[10px] text-zinc-500">conf. {h.confidence_score.toFixed(0)}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-zinc-400">{h.status}</p>
                      <p className="text-[10px] text-zinc-500">
                        ROI {h.roi != null && !Number.isNaN(h.roi) ? `${(h.roi * 100).toFixed(1)}%` : "—"}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {!result && !loading && !error && (
          <div className="rounded-2xl border border-dashed border-zinc-700/80 bg-zinc-900/20 px-6 py-16 text-center">
            <p className="text-sm text-zinc-500">
              Elige un perfil y pulsa <span className="text-zinc-300">Generar combinada</span> para ver la
              propuesta del motor.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
