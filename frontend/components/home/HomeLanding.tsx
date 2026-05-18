import Link from "next/link";

import { TestimonialCarousel } from "@/components/home/TestimonialCarousel";
import type { HomeFeaturedSnapshot, HomePageData } from "@/lib/home/getHomePageData";
import {
  valueGradeCardClasses,
  valueGradeHeroBadgeClasses,
  valueGradeShortLabel,
  type ValueGrade,
} from "@/lib/valueBets/evPresentation";

function formatKickoff(iso: string): string {
  try {
    const d = new Date(iso);
    return new Intl.DateTimeFormat("es", {
      weekday: "short",
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  } catch {
    return iso;
  }
}

function gradeOrDefault(g?: string): ValueGrade {
  if (g === "elite" || g === "high" || g === "good" || g === "risky") {
    return g;
  }
  return "good";
}

function FeaturedMatchCard({ f }: { f: HomeFeaturedSnapshot }) {
  const g = gradeOrDefault(f.value_grade);
  const probPct = Math.round(f.probabilidad * 1000) / 10;
  const barW = Math.min(100, Math.max(8, probPct));

  return (
    <div className="relative mx-auto max-w-4xl">
      <div className="pointer-events-none absolute -inset-1 rounded-[2rem] bg-gradient-to-r from-fuchsia-500/20 via-violet-500/25 to-cyan-500/20 opacity-90 blur-2xl" />
      <div
        className={`relative overflow-x-clip rounded-[1.75rem] border bg-zinc-950/80 p-8 shadow-2xl backdrop-blur-2xl sm:p-10 ${valueGradeCardClasses(g)}`}
      >
        <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-violet-600/15 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -left-16 h-56 w-56 rounded-full bg-cyan-500/10 blur-3xl" />

        <div className="relative z-[1] flex min-w-0 flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-white/5 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400 ring-1 ring-white/10">
                Partido del día
              </span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${valueGradeHeroBadgeClasses(g)}`}
              >
                IA · {valueGradeShortLabel(g)}
              </span>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{f.liga}</p>
              <h3 className="mt-2 text-2xl font-black tracking-tight text-white sm:text-3xl md:text-4xl">
                {f.equipo_local}
                <span className="mx-2 font-light text-zinc-600">vs</span>
                {f.equipo_visitante}
              </h3>
              <p className="mt-2 text-sm text-cyan-200/90">{formatKickoff(f.fecha)}</p>
            </div>
            <div className="inline-flex flex-wrap gap-2">
              <span className="rounded-xl border border-white/10 bg-black/30 px-3 py-1.5 text-xs text-zinc-200">
                {f.mercado} · <span className="font-semibold text-white">{f.pick}</span>
              </span>
              <span className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-200">
                Cuota @{f.cuota.toFixed(2)}
              </span>
            </div>
          </div>

          <div className="grid w-full min-w-0 max-w-sm shrink-0 grid-cols-2 gap-4 sm:grid-cols-2">
            <div className="min-w-0 rounded-2xl border border-white/10 bg-black/40 p-4 ring-1 ring-white/[0.04]">
              <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">Prob. modelo</p>
              <p className="mt-1 text-2xl font-black tabular-nums text-white">{probPct}%</p>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-zinc-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-violet-500 transition-all duration-700"
                  style={{ width: `${barW}%` }}
                />
              </div>
            </div>
            <div className="min-w-0 overflow-visible rounded-2xl border border-white/10 bg-black/40 p-4 ring-1 ring-white/[0.04]">
              <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">EV estimado</p>
              <p className="mt-1 break-words text-xl font-black tabular-nums tracking-tight text-emerald-300 sm:text-2xl">
                +{f.ev_pct.toFixed(1)}%
              </p>
              <p className="mt-2 text-[10px] leading-snug text-zinc-500">Edge vs cuota implícita</p>
            </div>
          </div>
        </div>

        <div className="relative z-[2] mt-8 flex flex-wrap gap-3 border-t border-white/[0.06] pt-6">
          <Link
            href="/value"
            className="relative z-10 inline-flex min-h-[44px] flex-1 min-w-[140px] items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 text-sm font-semibold text-white transition hover:border-cyan-500/40 hover:bg-cyan-500/10"
          >
            Ver más value bets
          </Link>
          <Link
            href="/acca"
            className="relative z-10 inline-flex min-h-[44px] flex-1 min-w-[160px] items-center justify-center rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 px-4 py-2.5 text-sm font-bold text-white shadow-lg shadow-fuchsia-900/40 transition hover:brightness-110"
          >
            Llevarlo al ACCA IA
          </Link>
        </div>
      </div>
    </div>
  );
}

function MetricMini({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent: "cyan" | "violet" | "emerald" | "amber";
}) {
  const ring =
    accent === "cyan"
      ? "from-cyan-500/30 to-blue-500/20"
      : accent === "violet"
        ? "from-violet-500/30 to-fuchsia-500/20"
        : accent === "emerald"
          ? "from-emerald-500/25 to-teal-500/15"
          : "from-amber-500/25 to-orange-500/15";
  return (
    <div className="group relative">
      <div
        className={`pointer-events-none absolute -inset-px rounded-2xl bg-gradient-to-br opacity-0 blur transition duration-500 group-hover:opacity-100 ${ring}`}
      />
      <div className="relative rounded-2xl border border-white/[0.06] bg-zinc-900/60 p-5 backdrop-blur-md transition duration-300 hover:border-white/12 hover:bg-zinc-900/80">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-500">{label}</p>
        <p className="mt-2 text-2xl font-black tabular-nums tracking-tight text-white sm:text-3xl">{value}</p>
        {sub ? <p className="mt-1 text-[11px] text-zinc-500">{sub}</p> : null}
      </div>
    </div>
  );
}

function DashStat({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint: string;
  accent?: boolean;
}) {
  return (
    <div
      className={[
        "rounded-2xl border p-5 backdrop-blur-md transition duration-300 hover:border-white/15",
        accent
          ? "border-emerald-500/20 bg-gradient-to-br from-emerald-500/[0.07] to-zinc-900/50"
          : "border-white/[0.06] bg-zinc-900/50 hover:bg-zinc-900/70",
      ].join(" ")}
    >
      <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">{label}</p>
      <p className="mt-2 text-2xl font-black tabular-nums text-white">{value}</p>
      <p className="mt-1 text-[11px] text-zinc-600">{hint}</p>
    </div>
  );
}

const STEPS = [
  {
    n: "01",
    title: "Analizamos miles de partidos",
    body: "Datos en vivo y modelos probabilísticos para cada competición.",
    icon: "◎",
  },
  {
    n: "02",
    title: "Detectamos value bets",
    body: "Comparamos cuota vs probabilidad y destacamos el EV real.",
    icon: "◆",
  },
  {
    n: "03",
    title: "Construimos ACCAs inteligentes",
    body: "Perfiles de riesgo y picks diversos por fixture, sin adivinar.",
    icon: "✦",
  },
  {
    n: "04",
    title: "Guardamos tu historial",
    body: "Combinadas generadas con fecha, cuota y EV para tu demo.",
    icon: "▣",
  },
] as const;

export function HomeLanding({ data }: { data: HomePageData }) {
  const evMedio =
    data.avg_ev != null ? `+${(data.avg_ev * 100).toFixed(1)}%` : "—";
  const accas =
    data.acca_history_count != null ? String(data.acca_history_count) : "—";
  const accaN = data.acca_history_count ?? 0;
  const acca_history_bar_pct = Math.min(100, Math.max(10, accaN * 6));
  const acca_history_bar_label = data.acca_history_count != null ? String(accaN) : "N/D";

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050508] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_120%_80%_at_50%_-20%,rgba(124,58,237,0.22),transparent_55%),radial-gradient(ellipse_80%_50%_at_100%_0%,rgba(6,182,212,0.12),transparent_45%),radial-gradient(ellipse_60%_40%_at_0%_100%,rgba(236,72,153,0.08),transparent_40%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.03)_0%,transparent_28%,transparent_100%)]" />

      <div className="relative mx-auto max-w-6xl px-4 pb-24 pt-14 sm:px-6 lg:px-8 lg:pb-32 lg:pt-20">
        {/* HERO */}
        <header className="text-center animate-home-fade">
          <h1 className="mx-auto max-w-4xl text-4xl font-black leading-[1.08] tracking-tight text-balance sm:text-5xl lg:text-6xl">
            <span className="bg-gradient-to-r from-white via-zinc-100 to-zinc-400 bg-clip-text text-transparent">
              Prediktia
            </span>{" "}
            <span className="bg-gradient-to-r from-cyan-300 via-violet-300 to-fuchsia-400 bg-clip-text text-transparent">
              Intelligence
            </span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg font-medium leading-relaxed text-zinc-300 sm:text-xl">
            Predicciones deportivas impulsadas por IA y valor esperado real.
          </p>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-zinc-500 sm:text-[15px]">
            Modelos Poisson + análisis probabilístico + gestión de riesgo automatizada para detectar apuestas con edge
            positivo.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row sm:gap-5">
            <Link
              href="/acca"
              className="inline-flex min-w-[200px] items-center justify-center rounded-2xl bg-gradient-to-r from-violet-600 via-fuchsia-600 to-violet-600 px-8 py-3.5 text-sm font-bold text-white shadow-[0_0_40px_-8px_rgba(168,85,247,0.55)] transition hover:brightness-110 hover:shadow-[0_0_48px_-6px_rgba(217,70,239,0.5)]"
            >
              Explorar ACCA IA
            </Link>
            <Link
              href="/value"
              className="inline-flex min-w-[180px] items-center justify-center rounded-2xl border border-white/15 bg-white/[0.04] px-8 py-3.5 text-sm font-semibold text-white backdrop-blur-sm transition hover:border-cyan-400/40 hover:bg-cyan-500/10"
            >
              Ver estadísticas
            </Link>
          </div>

          {data.error ? (
            <p className="mt-6 text-xs text-amber-400/90">
              Motor en pausa: {data.error}. Revisá el backend o <Link href="/matches" className="underline">partidos</Link>.
            </p>
          ) : null}

          <div className="mx-auto mt-14 grid max-w-4xl grid-cols-2 gap-4 sm:grid-cols-4">
            <MetricMini label="ACCAs" value={accas} sub="Combinadas en historial" accent="emerald" />
            <MetricMini label="Hitrate" value="—" sub="Métricas en vivo (próximo)" accent="amber" />
            <MetricMini
              label="Partidos analizados"
              value={data.picks_analyzed ? String(data.picks_analyzed) : "0"}
              sub={data.value_date ? `Corte ${data.value_date}` : "Picks del motor hoy"}
              accent="cyan"
            />
            <MetricMini
              label="Ligas monitoreadas"
              value={data.leagues_monitored ? String(data.leagues_monitored) : "—"}
              sub="Competiciones distintas"
              accent="violet"
            />
          </div>
        </header>

        {/* Partido del día */}
        <section className="mt-24 sm:mt-28">
          <div className="mb-10 text-center">
            <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">Partido del día</h2>
            <p className="mx-auto mt-2 max-w-lg text-sm text-zinc-500">
              Selección automática según EV, confianza y contexto editorial del calendario.
            </p>
          </div>
          {data.featured ? (
            <FeaturedMatchCard f={data.featured} />
          ) : (
            <div className="mx-auto max-w-xl rounded-3xl border border-white/10 bg-zinc-900/50 p-10 text-center text-zinc-400">
              <p className="text-sm">No hay picks destacados en este momento.</p>
              <Link href="/value" className="mt-4 inline-block text-sm font-semibold text-cyan-400 hover:text-cyan-300">
                Ir al panel Value →
              </Link>
            </div>
          )}
        </section>

        {/* Cómo funciona */}
        <section className="mt-28 sm:mt-32">
          <h2 className="text-center text-2xl font-bold tracking-tight sm:text-3xl">Cómo funciona Prediktia</h2>
          <p className="mx-auto mt-2 max-w-xl text-center text-sm text-zinc-500">
            Del dato crudo a la decisión: un flujo pensado para apostadores serios.
          </p>
          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s) => (
              <div
                key={s.n}
                className="group relative overflow-hidden rounded-2xl border border-white/[0.06] bg-zinc-900/40 p-6 backdrop-blur-md transition duration-300 hover:border-violet-500/25 hover:bg-zinc-900/70"
              >
                <div className="text-2xl text-zinc-600 transition group-hover:text-violet-400">{s.icon}</div>
                <p className="mt-3 text-[10px] font-bold uppercase tracking-widest text-violet-400/80">{s.n}</p>
                <h3 className="mt-2 text-base font-bold text-white">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-zinc-500">{s.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Credibilidad / métricas dashboard */}
        <section className="mt-28 sm:mt-32">
          <h2 className="text-center text-2xl font-bold tracking-tight sm:text-3xl">Rendimiento y credibilidad</h2>
          <p className="mx-auto mt-2 max-w-lg text-center text-sm text-zinc-500">
            KPIs reales donde el backend ya expone datos; sin métricas inventadas.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <DashStat label="EV medio del día" value={evMedio} hint="Picks del motor value" />
            <DashStat label="ACCA generadas" value={accas} hint="Historial reciente (API)" />
            <DashStat label="Picks acertados" value="—" hint="Post-resultado (en roadmap)" />
            <DashStat label="Yield" value="—" hint="Sobre bankroll simulado" />
            <DashStat label="Winrate" value="—" hint="Agregado por mercado" />
            <DashStat
              label="Ligas monitoreadas"
              value={data.leagues_monitored ? String(data.leagues_monitored) : "—"}
              hint="Competiciones en el value del día"
            />
            <DashStat label="EV medio (hoy)" value={evMedio} hint="Sobre picks publicados" accent />
            <DashStat
              label="Partidos analizados"
              value={String(data.picks_analyzed || 0)}
              hint={data.value_date ? `Fecha motor ${data.value_date}` : "Pipeline activo"}
              accent
            />
          </div>
          <div className="mt-8 rounded-3xl border border-white/[0.07] bg-gradient-to-b from-zinc-900/80 to-black/40 p-8 backdrop-blur-xl">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Intensidad pipeline</p>
                <p className="mt-1 text-3xl font-black text-white">{data.picks_analyzed || 0}</p>
                <p className="text-sm text-zinc-500">Picks procesados · {accas} ACCA en historial</p>
              </div>
            </div>
            <div className="mt-6 space-y-3">
              <div>
                <div className="mb-1 flex justify-between text-[11px] text-zinc-500">
                  <span>Cobertura picks</span>
                  <span>{data.picks_analyzed || 0}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-zinc-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-violet-500 transition-all duration-700"
                    style={{
                      width: `${Math.min(100, Math.max(8, (data.picks_analyzed || 0) * 3))}%`,
                    }}
                  />
                </div>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-[11px] text-zinc-500">
                  <span>Historial ACCA</span>
                  <span>{acca_history_bar_label}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-zinc-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-700"
                    style={{
                      width: `${acca_history_bar_pct}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Testimonios */}
        <section className="mt-28 sm:mt-32">
          <h2 className="text-center text-2xl font-bold tracking-tight sm:text-3xl">Quiénes priorizan el dato</h2>
          <p className="mx-auto mt-2 max-w-lg text-center text-sm text-zinc-500">
            Opiniones breves de usuarios que priorizan datos sobre ruido.
          </p>
          <div className="mt-12">
            <TestimonialCarousel />
          </div>
        </section>

        {/* CTA final */}
        <section className="mt-28 text-center sm:mt-36">
          <div className="relative mx-auto max-w-3xl overflow-hidden rounded-[2rem] border border-white/10 bg-gradient-to-b from-zinc-900/90 to-black/80 px-6 py-14 shadow-[0_0_80px_-20px_rgba(139,92,246,0.35)] sm:px-12">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(34,211,238,0.12),transparent_45%)]" />
            <h2 className="relative text-2xl font-black tracking-tight text-balance sm:text-3xl">
              Empieza a usar apuestas con datos, no intuición.
            </h2>
            <p className="relative mx-auto mt-4 max-w-lg text-sm text-zinc-400">
              Explorá el ACCA IA con perfiles de riesgo o revisá el value del día antes de jugar.
            </p>
            <div className="relative mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link
                href="/planes"
                className="inline-flex min-w-[200px] items-center justify-center rounded-2xl bg-white px-8 py-3.5 text-sm font-bold text-zinc-950 shadow-xl transition hover:bg-zinc-100"
              >
                Probar gratis
              </Link>
              <Link
                href="/acca"
                className="inline-flex min-w-[200px] items-center justify-center rounded-2xl border border-white/20 bg-transparent px-8 py-3.5 text-sm font-bold text-white transition hover:bg-white/10"
              >
                Explorar ACCA IA
              </Link>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
