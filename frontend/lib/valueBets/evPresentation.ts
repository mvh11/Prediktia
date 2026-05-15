/**
 * Presentación por grado de valor (backend `value_grade`), según magnitud de EV.
 * Paleta premium: GOOD azul suave, HIGH verde, RISKY naranja suave, ELITE violeta.
 */
export type ValueGrade = "risky" | "good" | "high" | "elite";

export function valueGradeLabel(grade: ValueGrade): string {
  switch (grade) {
    case "elite":
      return "ELITE VALUE";
    case "high":
      return "HIGH VALUE";
    case "good":
      return "GOOD VALUE";
    default:
      return "RISKY VALUE";
  }
}

/** Etiqueta corta para cards (portada). */
export function valueGradeShortLabel(grade: ValueGrade): string {
  switch (grade) {
    case "elite":
      return "ELITE";
    case "high":
      return "HIGH";
    case "good":
      return "GOOD";
    default:
      return "RISKY";
  }
}

/** Contenedor de card: borde / fondo sutil (dark premium). */
export function valueGradeCardClasses(grade: ValueGrade): string {
  switch (grade) {
    case "elite":
      return "border-violet-500/35 bg-gradient-to-b from-violet-500/[0.08] to-zinc-950/40 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]";
    case "high":
      return "border-emerald-500/30 bg-gradient-to-b from-emerald-500/[0.07] to-zinc-950/40 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]";
    case "good":
      return "border-sky-500/35 bg-gradient-to-b from-sky-500/[0.08] to-zinc-950/40 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]";
    default:
      return "border-orange-500/25 bg-gradient-to-b from-orange-500/[0.06] to-zinc-950/40 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]";
  }
}

/** Badge principal del grado (compacto, legible). */
export function valueGradeHeroBadgeClasses(grade: ValueGrade): string {
  switch (grade) {
    case "elite":
      return "bg-violet-500/25 text-violet-100 ring-1 ring-violet-400/40";
    case "high":
      return "bg-emerald-500/20 text-emerald-100 ring-1 ring-emerald-400/35";
    case "good":
      return "bg-sky-500/20 text-sky-100 ring-1 ring-sky-400/35";
    default:
      return "bg-orange-500/15 text-orange-100 ring-1 ring-orange-400/30";
  }
}

/** Celda / bloque EV destacado. */
export function valueGradeEvCellClasses(grade: ValueGrade): string {
  switch (grade) {
    case "elite":
      return "bg-violet-500/10 text-violet-50 ring-1 ring-violet-400/25";
    case "high":
      return "bg-emerald-500/10 text-emerald-50 ring-1 ring-emerald-400/25";
    case "good":
      return "bg-sky-500/10 text-sky-50 ring-1 ring-sky-400/25";
    default:
      return "bg-orange-500/10 text-orange-50 ring-1 ring-orange-400/20";
  }
}

export function valueGradeGlowBar(grade: ValueGrade): string {
  switch (grade) {
    case "elite":
      return "from-violet-400/90 via-fuchsia-500/50 to-transparent";
    case "high":
      return "from-emerald-400/90 via-teal-400/40 to-transparent";
    case "good":
      return "from-sky-400/85 via-cyan-400/35 to-transparent";
    default:
      return "from-orange-400/80 via-amber-500/30 to-transparent";
  }
}

/** Chip secundario “VALUE” (más pequeño, discreto). */
export function valueGradeValueChipClasses(grade: ValueGrade): string {
  switch (grade) {
    case "elite":
      return "border-violet-500/25 bg-black/30 text-violet-200/90";
    case "high":
      return "border-emerald-500/20 bg-black/30 text-emerald-200/85";
    case "good":
      return "border-sky-500/20 bg-black/30 text-sky-200/85";
    default:
      return "border-orange-500/20 bg-black/30 text-orange-200/80";
  }
}
