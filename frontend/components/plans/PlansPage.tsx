"use client";

import { useCallback, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  PLANS,
  normalizeTier,
  startPremiumCheckout,
  startVipContact,
  tierLabel,
  tierRank,
} from "@/lib/plans";

export function PlansPage() {
  const { user } = useAuth();
  const currentTier = normalizeTier(user?.tier);
  const currentRank = tierRank(currentTier);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const handleCta = useCallback(
    async (variant: "free" | "premium" | "vip", planId: string) => {
      if (planId === currentTier) return;
      setNotice(null);
      setBusy(planId);
      try {
        const result =
          variant === "premium" ? await startPremiumCheckout() : await startVipContact();
        setNotice(result.message);
      } finally {
        setBusy(null);
      }
    },
    [currentTier],
  );

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050508] text-white">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(139,92,246,0.18),transparent)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-32 top-1/3 h-96 w-96 rounded-full bg-cyan-500/10 blur-3xl"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -left-24 bottom-0 h-80 w-80 rounded-full bg-violet-600/10 blur-3xl"
        aria-hidden
      />

      <div className="relative mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14 lg:py-16">
        <header className="mx-auto max-w-2xl text-center">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-400/90">
            Suscripciones
          </p>
          <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">
            Elige tu{" "}
            <span className="bg-gradient-to-r from-cyan-300 via-violet-300 to-fuchsia-300 bg-clip-text text-transparent">
              plan Prediktia
            </span>
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-zinc-400 sm:text-base">
            Value bets, Smart ACCA e historial según tu nivel. Pagos con Transbank — próximamente.
          </p>
          {user ? (
            <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm">
              <span className="text-zinc-400">{user.display_name || user.email}</span>
              <span className="text-zinc-600">·</span>
              <span className="rounded-md bg-violet-500/20 px-2 py-0.5 text-xs font-bold text-violet-200 ring-1 ring-violet-400/30">
                {user.tier_label || tierLabel(currentTier)}
              </span>
            </div>
          ) : null}
        </header>

        {notice ? (
          <div
            role="status"
            className="mx-auto mt-8 max-w-2xl rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100"
          >
            {notice}
          </div>
        ) : null}

        <div className="mt-12 grid gap-6 lg:grid-cols-3 lg:gap-5 lg:items-stretch">
          {PLANS.map((plan) => {
            const isActive = plan.id === currentTier;
            const isUpgrade = tierRank(plan.id) > currentRank;
            const isDowngrade = tierRank(plan.id) < currentRank;

            return (
              <article
                key={plan.id}
                className={[
                  "relative flex flex-col rounded-2xl p-[1px]",
                  isActive ? `bg-gradient-to-b ${plan.gradient}` : "bg-white/[0.08]",
                ].join(" ")}
              >
                <div
                  className={[
                    "relative flex h-full flex-col rounded-2xl border bg-zinc-950/90 p-6 sm:p-7",
                    plan.glow,
                    isActive ? `border-transparent ring-2 ${plan.ring}` : "border-white/[0.06]",
                  ].join(" ")}
                >
                  {plan.badge ? (
                    <span
                      className={[
                        "absolute -top-3 left-6 rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wider",
                        plan.id === "premium"
                          ? "bg-gradient-to-r from-cyan-500 to-violet-500 text-white"
                          : plan.id === "vip"
                            ? "bg-gradient-to-r from-violet-500 to-rose-500 text-white"
                            : "bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-400/30",
                      ].join(" ")}
                    >
                      {isActive ? "Tu plan" : plan.badge}
                    </span>
                  ) : null}

                  <div className="mb-5 flex items-start justify-between gap-3 pt-2">
                    <div>
                      <span className="text-2xl" aria-hidden>
                        {plan.icon}
                      </span>
                      <h2 className="mt-2 text-xl font-bold">{plan.name}</h2>
                      <p className="mt-1 text-sm text-zinc-500">{plan.tagline}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-black tabular-nums">{plan.priceLabel}</p>
                      <p className="text-[10px] text-zinc-500">{plan.priceNote}</p>
                    </div>
                  </div>

                  <ul className="mb-8 flex-1 space-y-3 text-sm">
                    {plan.features.map((f) => (
                      <li key={f.label} className="flex items-start gap-2.5">
                        <span
                          className={[
                            "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-xs font-bold",
                            f.included
                              ? "bg-emerald-500/15 text-emerald-300"
                              : "bg-zinc-800 text-zinc-600",
                          ].join(" ")}
                          aria-hidden
                        >
                          {f.included ? "✓" : "—"}
                        </span>
                        <span
                          className={
                            f.highlight && f.included
                              ? "font-medium text-white"
                              : f.included
                                ? "text-zinc-300"
                                : "text-zinc-600"
                          }
                        >
                          {f.label}
                        </span>
                      </li>
                    ))}
                  </ul>

                  <button
                    type="button"
                    disabled={isActive || busy === plan.id}
                    onClick={() => {
                      if (plan.ctaVariant === "free") return;
                      void handleCta(plan.ctaVariant, plan.id);
                    }}
                    className={[
                      "w-full rounded-xl px-4 py-3 text-sm font-semibold transition",
                      isActive
                        ? "cursor-default bg-white/10 text-zinc-400 ring-1 ring-white/15"
                        : isDowngrade
                          ? "bg-zinc-900 text-zinc-500 ring-1 ring-white/10 hover:bg-zinc-800"
                          : plan.ctaVariant === "premium"
                            ? "bg-gradient-to-r from-cyan-500 to-violet-500 text-white shadow-[0_0_28px_-8px_rgba(56,189,248,0.6)] hover:opacity-90"
                            : "bg-gradient-to-r from-violet-500 to-rose-500 text-white shadow-[0_0_28px_-8px_rgba(168,85,247,0.5)] hover:opacity-90",
                      busy === plan.id ? "opacity-60" : "",
                    ].join(" ")}
                  >
                    {isActive
                      ? "Plan activo"
                      : isUpgrade
                        ? busy === plan.id
                          ? "Procesando…"
                          : plan.cta
                        : plan.ctaVariant === "free"
                          ? "Incluido"
                          : plan.cta}
                  </button>
                </div>
              </article>
            );
          })}
        </div>

        <p className="mx-auto mt-10 max-w-xl text-center text-xs text-zinc-600">
          Los pagos con Transbank (Webpay Plus) se activarán en una próxima versión. No se almacenan
          datos de tarjeta en Prediktia.
        </p>
      </div>
    </div>
  );
}
