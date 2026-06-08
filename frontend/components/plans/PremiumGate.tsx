"use client";

import Link from "next/link";
import type { ReactNode } from "react";

type PremiumGateProps = {
  title?: string;
  description?: string;
  feature?: string;
  children?: ReactNode;
  compact?: boolean;
};

export function PremiumGate({
  title = "Función Premium",
  description = "Mejora tu plan para desbloquear esta función.",
  feature,
  children,
  compact = false,
}: PremiumGateProps) {
  return (
    <div
      className={[
        "rounded-2xl border border-violet-500/30 bg-gradient-to-b from-violet-500/[0.12] to-zinc-950/80 backdrop-blur-sm",
        compact ? "p-4" : "p-6 sm:p-8",
      ].join(" ")}
    >
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-500/20 text-lg ring-1 ring-violet-400/40">
          🔒
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-300/90">
            {feature ?? "Premium"}
          </p>
          <h3 className="mt-1 text-lg font-bold text-white">{title}</h3>
          <p className="mt-2 text-sm leading-relaxed text-zinc-400">{description}</p>
          {children}
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href="/planes"
              className="inline-flex rounded-xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-2.5 text-sm font-semibold text-white shadow-[0_0_24px_-6px_rgba(139,92,246,0.7)] transition hover:opacity-90"
            >
              Ver planes
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
